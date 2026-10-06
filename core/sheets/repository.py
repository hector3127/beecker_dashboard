"""Lectura y escritura de hojas con la API de Google Sheets."""

import logging
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any, Final

from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError

from core.exceptions import (
    SheetAuthenticationError,
    SheetColumnNotFoundError,
    SheetNotFoundError,
    SheetsError,
    SpreadsheetNotFoundError,
)
from core.sheets.read_cache import SheetReadCache
from core.utils.cell_types import CellValue, SheetRow
from core.utils.dates import format_sheet_datetime
from core.utils.text import to_text

"""BKD.004.005 - Repositorio de Google Sheets
Unica capa autorizada a tocar la API de Sheets, igual que SheetService.gs.
Todo modulo de negocio lee y escribe a traves de esta clase.
"""

logger = logging.getLogger(__name__)

HEADER_BACKGROUND: Final[dict[str, float]] = {
    "red": 0.169,
    "green": 0.169,
    "blue": 0.180,
}

HEADER_FOREGROUND: Final[dict[str, float]] = {
    "red": 1.0,
    "green": 1.0,
    "blue": 1.0,
}

AUTH_ERROR_STATUSES: Final[frozenset[int]] = frozenset({401, 403})

NOT_FOUND_STATUS: Final[int] = 404

ALPHABET_SIZE: Final[int] = 26


class GoogleSheetRepository:
    """Acceso a un Spreadsheet con cache por instancia y compartida."""

    def __init__(
        self,
        service: Any,
        spreadsheet_id: str,
        read_cache: SheetReadCache | None = None,
    ) -> None:
        self._service = service
        self._spreadsheet_id = spreadsheet_id
        self._shared_cache = read_cache or SheetReadCache(spreadsheet_id, 0)
        self._sheet_ids: dict[str, int] | None = None
        self._values_by_sheet: dict[str, list[list[CellValue]]] = {}

    def sheet_exists(self, sheet_name: str) -> bool:
        """
        Indica si la hoja existe en el Spreadsheet.

        Args:
            sheet_name: Nombre de la hoja.

        Returns:
            True cuando la hoja existe.
        """
        return sheet_name in self._load_sheet_ids()

    def prefetch(self, sheet_names: Iterable[str]) -> None:
        """
        Lee varias hojas en una sola llamada a la API.

        Las hojas que no existen se omiten sin error.

        Args:
            sheet_names: Nombres de las hojas a precargar.
        """
        pending_names = [
            sheet_name
            for sheet_name in dict.fromkeys(sheet_names)
            if self.sheet_exists(sheet_name)
            and sheet_name not in self._values_by_sheet
        ]

        pending_names = self._take_shared_hits(pending_names)

        if not pending_names:
            return

        response = self._execute(
            self._service.spreadsheets()
            .values()
            .batchGet(
                spreadsheetId=self._spreadsheet_id,
                ranges=[quote_sheet_name(name) for name in pending_names],
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="SERIAL_NUMBER",
            ),
        )

        value_ranges = response.get("valueRanges", [])

        for sheet_name, value_range in zip(
            pending_names,
            value_ranges,
            strict=True,
        ):
            values = value_range.get("values", [])
            self._values_by_sheet[sheet_name] = values
            self._shared_cache.set_values(sheet_name, values)

    def list_sheet_names(self) -> list[str]:
        """
        Nombres de las hojas en el orden de las pestanas (ss.getSheets()).

        Returns:
            Los nombres de las hojas.
        """
        return list(self._load_sheet_ids())

    def read_previews(
        self,
        sheet_names: Sequence[str],
        row_count: int,
        column_count: int,
    ) -> dict[str, list[list[CellValue]]]:
        """
        Lee el inicio de varias hojas en una sola llamada.

        Args:
            sheet_names: Hojas a leer.
            row_count: Filas desde la 1.
            column_count: Columnas desde la A.

        Returns:
            Hoja -> celdas leidas (sin las filas y columnas vacias al final).
        """
        names = [name for name in sheet_names if self.sheet_exists(name)]

        if not names:
            return {}

        last_cell = f"{column_letter(column_count)}{row_count}"
        response = self._execute(
            self._service.spreadsheets()
            .values()
            .batchGet(
                spreadsheetId=self._spreadsheet_id,
                ranges=[
                    f"{quote_sheet_name(name)}!A1:{last_cell}" for name in names
                ],
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="SERIAL_NUMBER",
            ),
        )

        return {
            name: value_range.get("values", [])
            for name, value_range in zip(
                names,
                response.get("valueRanges", []),
                strict=True,
            )
        }

    def read_values(self, sheet_name: str) -> list[list[CellValue]]:
        """
        Lee todas las celdas con datos de la hoja.

        Args:
            sheet_name: Nombre de la hoja.

        Returns:
            Matriz de valores; las filas pueden tener distinto largo.

        Raises:
            SheetNotFoundError: Cuando la hoja no existe.
        """
        if not self.sheet_exists(sheet_name):
            raise SheetNotFoundError(f"Hoja no encontrada: {sheet_name}")

        self.prefetch([sheet_name])

        return self._values_by_sheet[sheet_name]

    def read_as_objects(self, sheet_name: str) -> list[SheetRow]:
        """
        Lee la hoja como lista de diccionarios usando la fila 1.

        Equivale a readSheetAsObjects() y omite las filas vacias.

        Args:
            sheet_name: Nombre de la hoja.

        Returns:
            Una lista con un diccionario encabezado -> valor por fila.

        Raises:
            SheetNotFoundError: Cuando la hoja no existe.
        """
        values = self.read_values(sheet_name)

        if len(values) < 2:
            return []

        headers = [to_text(header) for header in values[0]]

        return [
            build_row_object(headers, row)
            for row in values[1:]
            if any(cell != "" and cell is not None for cell in row)
        ]

    def ensure_sheet(self, sheet_name: str, headers: Sequence[str]) -> bool:
        """
        Crea la hoja con encabezados si todavia no existe.

        Args:
            sheet_name: Nombre de la hoja.
            headers: Encabezados de la fila 1.

        Returns:
            True si la hoja se creo en esta llamada.
        """
        was_created = False

        if not self.sheet_exists(sheet_name):
            self._add_sheet(sheet_name)
            was_created = True

        current_values = self.read_values(sheet_name)
        first_cell = current_values[0][0] if current_values else ""

        if first_cell in ("", None):
            self._write_headers(sheet_name, headers)

        return was_created

    def append_row(
        self,
        sheet_name: str,
        values: Sequence[CellValue | datetime],
    ) -> None:
        """
        Agrega una fila al final de la hoja, como sheet.appendRow().

        Args:
            sheet_name: Nombre de la hoja.
            values: Valores de la fila en el orden de las columnas.
        """
        self._execute(
            self._service.spreadsheets()
            .values()
            .append(
                spreadsheetId=self._spreadsheet_id,
                range=f"{quote_sheet_name(sheet_name)}!A1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [serialize_row(values)]},
            ),
        )

        self._forget(sheet_name)

    def upsert_row(
        self,
        sheet_name: str,
        id_column: str,
        data: Mapping[str, CellValue | datetime],
    ) -> None:
        """
        Actualiza la fila con el mismo ID o la agrega si no existe.

        Equivale a upsertRow() de SheetService.gs, sin el historico.

        Args:
            sheet_name: Nombre de la hoja maestra.
            id_column: Encabezado de la columna ID.
            data: Valores a escribir por encabezado.

        Raises:
            SheetColumnNotFoundError: Cuando la columna ID no existe.
        """
        values = self.read_values(sheet_name)
        headers = [to_text(header) for header in values[0]] if values else []

        if id_column not in headers:
            raise SheetColumnNotFoundError(
                f"Columna ID no encontrada: {id_column}",
            )

        id_index = headers.index(id_column)
        target_row_number = find_row_number(
            values,
            id_index,
            data.get(id_column),
        )
        row_values = [data.get(header, "") for header in headers]

        if target_row_number is None:
            self.append_row(sheet_name, row_values)
            return

        self._execute(
            self._service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self._spreadsheet_id,
                range=(f"{quote_sheet_name(sheet_name)}!A{target_row_number}"),
                valueInputOption="USER_ENTERED",
                body={"values": [serialize_row(row_values)]},
            ),
        )

        self._forget(sheet_name)

    def write_cell(
        self,
        sheet_name: str,
        row_number: int,
        column_number: int,
        value: CellValue,
    ) -> None:
        """
        Escribe una sola celda, como range.setValue().

        Args:
            sheet_name: Nombre de la hoja.
            row_number: Fila en base 1.
            column_number: Columna en base 1.
            value: Valor a escribir.
        """
        cell = f"{column_letter(column_number)}{row_number}"
        self._execute(
            self._service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self._spreadsheet_id,
                range=f"{quote_sheet_name(sheet_name)}!{cell}",
                valueInputOption="USER_ENTERED",
                body={"values": [serialize_row([value])]},
            ),
        )

        self._forget(sheet_name)

    def write_row(
        self,
        sheet_name: str,
        row_number: int,
        values: Sequence[CellValue | datetime],
    ) -> None:
        """
        Escribe una fila desde la columna A, como getRange(...).setValues().

        Args:
            sheet_name: Nombre de la hoja.
            row_number: Fila en base 1.
            values: Valores de la fila.
        """
        self._execute(
            self._service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self._spreadsheet_id,
                range=f"{quote_sheet_name(sheet_name)}!A{row_number}",
                valueInputOption="USER_ENTERED",
                body={"values": [serialize_row(values)]},
            ),
        )

        self._forget(sheet_name)

    def delete_sheet(self, sheet_name: str) -> None:
        """
        Elimina una hoja completa, como ss.deleteSheet().

        Args:
            sheet_name: Nombre de la hoja.

        Raises:
            SheetNotFoundError: Cuando la hoja no existe.
        """
        sheet_ids = self._load_sheet_ids()

        if sheet_name not in sheet_ids:
            raise SheetNotFoundError(f"Hoja no encontrada: {sheet_name}")

        self._execute(
            self._service.spreadsheets().batchUpdate(
                spreadsheetId=self._spreadsheet_id,
                body={
                    "requests": [
                        {"deleteSheet": {"sheetId": sheet_ids[sheet_name]}},
                    ],
                },
            ),
        )

        del sheet_ids[sheet_name]
        self._shared_cache.invalidate_sheet_ids()
        self._forget(sheet_name)

    def delete_row_range(
        self,
        sheet_name: str,
        first_row: int,
        row_count: int,
    ) -> None:
        """
        Elimina varias filas seguidas, como sheet.deleteRows(inicio, n).

        Args:
            sheet_name: Nombre de la hoja.
            first_row: Primera fila (base 1).
            row_count: Cuantas filas.

        Raises:
            SheetNotFoundError: Cuando la hoja no existe.
        """
        sheet_ids = self._load_sheet_ids()

        if sheet_name not in sheet_ids:
            raise SheetNotFoundError(f"Hoja no encontrada: {sheet_name}")

        if row_count <= 0:
            return

        self._execute(
            self._service.spreadsheets().batchUpdate(
                spreadsheetId=self._spreadsheet_id,
                body={
                    "requests": [
                        {
                            "deleteDimension": {
                                "range": {
                                    "sheetId": sheet_ids[sheet_name],
                                    "dimension": "ROWS",
                                    "startIndex": first_row - 1,
                                    "endIndex": first_row - 1 + row_count,
                                },
                            },
                        },
                    ],
                },
            ),
        )

        self._forget(sheet_name)

    def delete_row(self, sheet_name: str, row_number: int) -> None:
        """
        Elimina una fila completa, como sheet.deleteRow().

        Args:
            sheet_name: Nombre de la hoja.
            row_number: Fila en base 1.

        Raises:
            SheetNotFoundError: Cuando la hoja no existe.
        """
        sheet_ids = self._load_sheet_ids()

        if sheet_name not in sheet_ids:
            raise SheetNotFoundError(f"Hoja no encontrada: {sheet_name}")

        self._execute(
            self._service.spreadsheets().batchUpdate(
                spreadsheetId=self._spreadsheet_id,
                body={
                    "requests": [
                        {
                            "deleteDimension": {
                                "range": {
                                    "sheetId": sheet_ids[sheet_name],
                                    "dimension": "ROWS",
                                    "startIndex": row_number - 1,
                                    "endIndex": row_number,
                                },
                            },
                        },
                    ],
                },
            ),
        )

        self._forget(sheet_name)

    def _load_sheet_ids(self) -> dict[str, int]:
        """Lee una sola vez los nombres e IDs de las hojas existentes."""
        if self._sheet_ids is None:
            self._sheet_ids = self._shared_cache.get_sheet_ids()

        if self._sheet_ids is None:
            response = self._execute(
                self._service.spreadsheets().get(
                    spreadsheetId=self._spreadsheet_id,
                    fields="sheets.properties(sheetId,title)",
                ),
            )

            self._sheet_ids = {
                sheet["properties"]["title"]: sheet["properties"]["sheetId"]
                for sheet in response.get("sheets", [])
            }
            self._shared_cache.set_sheet_ids(self._sheet_ids)

        return self._sheet_ids

    def _take_shared_hits(self, sheet_names: list[str]) -> list[str]:
        """
        Carga desde la cache compartida las hojas que ya estan guardadas.

        Args:
            sheet_names: Hojas pendientes de leer.

        Returns:
            Las hojas que todavia hay que pedir a Google.
        """
        missing: list[str] = []

        for sheet_name in sheet_names:
            shared_values = self._shared_cache.get_values(sheet_name)

            if shared_values is None:
                missing.append(sheet_name)
            else:
                self._values_by_sheet[sheet_name] = shared_values

        return missing

    def _forget(self, sheet_name: str) -> None:
        """Descarta las lecturas de una hoja tras escribir en ella."""
        self._values_by_sheet.pop(sheet_name, None)
        self._shared_cache.invalidate_values(sheet_name)

    def _add_sheet(self, sheet_name: str) -> None:
        """Crea una hoja nueva con la fila 1 congelada."""
        response = self._execute(
            self._service.spreadsheets().batchUpdate(
                spreadsheetId=self._spreadsheet_id,
                body={
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {
                                    "title": sheet_name,
                                    "gridProperties": {
                                        "frozenRowCount": 1,
                                    },
                                },
                            },
                        },
                    ],
                },
            ),
        )

        new_properties = response["replies"][0]["addSheet"]["properties"]
        self._load_sheet_ids()[sheet_name] = new_properties["sheetId"]
        self._values_by_sheet[sheet_name] = []
        self._shared_cache.invalidate_sheet_ids()
        self._shared_cache.invalidate_values(sheet_name)

    def _write_headers(
        self,
        sheet_name: str,
        headers: Sequence[str],
    ) -> None:
        """Escribe y da formato a la fila de encabezados."""
        self._execute(
            self._service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self._spreadsheet_id,
                range=f"{quote_sheet_name(sheet_name)}!A1",
                valueInputOption="RAW",
                body={"values": [list(headers)]},
            ),
        )

        self._execute(
            self._service.spreadsheets().batchUpdate(
                spreadsheetId=self._spreadsheet_id,
                body={
                    "requests": [
                        build_header_format_request(
                            self._load_sheet_ids()[sheet_name],
                            len(headers),
                        ),
                    ],
                },
            ),
        )

        self._forget(sheet_name)

    def _execute(self, request: Any) -> Any:
        """
        Ejecuta una peticion y traduce los errores de Google.

        Args:
            request: Peticion construida con el cliente de Google.

        Returns:
            La respuesta JSON de la API.

        Raises:
            SheetsError: Cuando la API responde con error.
        """
        try:
            return request.execute()
        except HttpError as error:
            logger.warning(
                "Google Sheets respondio con error. status=%s",
                error.resp.status,
            )

            raise translate_http_error(error) from error
        except GoogleAuthError as error:
            logger.exception("Fallo la autenticacion con Google.")

            raise SheetAuthenticationError(
                "Revisa la cuenta de servicio configurada.",
            ) from error
        except (OSError, TimeoutError) as error:
            logger.exception("No hubo conexion con Google Sheets.")

            raise SheetsError(
                "No hubo conexion con Google Sheets.",
            ) from error


def translate_http_error(error: HttpError) -> SheetsError:
    """
    Convierte un HttpError de Google en una excepcion del proyecto.

    Args:
        error: Error devuelto por la API.

    Returns:
        La excepcion equivalente del proyecto.
    """
    status = int(error.resp.status)

    if status in AUTH_ERROR_STATUSES:
        return SheetAuthenticationError(
            "Comparte el Spreadsheet con el correo de la cuenta de "
            "servicio como editor.",
        )

    if status == NOT_FOUND_STATUS:
        return SpreadsheetNotFoundError(
            "Revisa GOOGLE_SPREADSHEET_ID en el archivo .env.",
        )

    return SheetsError(f"Google Sheets respondio con estatus {status}.")


def quote_sheet_name(sheet_name: str) -> str:
    """
    Escribe el nombre de hoja con comillas para usarlo en un rango A1.

    Args:
        sheet_name: Nombre de la hoja.

    Returns:
        El nombre entre comillas simples y con comillas internas dobles.
    """
    escaped_name = sheet_name.replace("'", "''")

    return f"'{escaped_name}'"


def column_letter(column_number: int) -> str:
    """
    Convierte un numero de columna (base 1) a letras A1 (1 -> A, 27 -> AA).

    Args:
        column_number: Numero de columna.

    Returns:
        Las letras de la columna.
    """
    letters = ""
    remaining = column_number

    while remaining > 0:
        remaining, remainder = divmod(remaining - 1, ALPHABET_SIZE)
        letters = chr(ord("A") + remainder) + letters

    return letters


def build_row_object(
    headers: Sequence[str],
    row: Sequence[CellValue],
) -> SheetRow:
    """
    Convierte una fila en diccionario, rellenando las celdas faltantes.

    La API de Sheets omite las celdas vacias al final de cada fila.

    Args:
        headers: Encabezados de la hoja.
        row: Valores de la fila.

    Returns:
        Diccionario encabezado -> valor.
    """
    row_object: SheetRow = {}

    for column_index, header in enumerate(headers):
        row_object[header] = (
            row[column_index] if column_index < len(row) else ""
        )

    return row_object


def find_row_number(
    values: Sequence[Sequence[CellValue]],
    id_index: int,
    id_value: CellValue | datetime,
) -> int | None:
    """
    Busca el numero de fila (base 1) cuyo ID coincide.

    Args:
        values: Matriz completa de la hoja, incluidos encabezados.
        id_index: Indice de la columna ID.
        id_value: Valor del ID buscado.

    Returns:
        El numero de fila en Sheets, o None si no existe.
    """
    for row_index, row in enumerate(values[1:], start=2):
        if id_index < len(row) and row[id_index] == id_value:
            return row_index

    return None


def serialize_row(values: Sequence[CellValue | datetime]) -> list[CellValue]:
    """
    Prepara los valores para enviarlos a la API de Sheets.

    Args:
        values: Valores de la fila; pueden incluir fechas.

    Returns:
        Valores serializables; las fechas van como texto reconocible.
    """
    serialized_values: list[CellValue] = []

    for value in values:
        if isinstance(value, datetime):
            serialized_values.append(format_sheet_datetime(value))
        elif value is None:
            serialized_values.append("")
        else:
            serialized_values.append(value)

    return serialized_values


def build_header_format_request(
    sheet_id: int,
    column_count: int,
) -> dict[str, Any]:
    """
    Construye el formato de encabezado usado por Setup.gs.

    Args:
        sheet_id: ID numerico de la hoja.
        column_count: Cantidad de columnas del encabezado.

    Returns:
        La peticion repeatCell para batchUpdate.
    """
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": column_count,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": HEADER_BACKGROUND,
                    "textFormat": {
                        "bold": True,
                        "foregroundColor": HEADER_FOREGROUND,
                    },
                },
            },
            "fields": ("userEnteredFormat(backgroundColor,textFormat)"),
        },
    }
