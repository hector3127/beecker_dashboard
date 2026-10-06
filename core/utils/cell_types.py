"""Tipos de los valores que regresa la API de Google Sheets."""

"""BKD.003.004 - Tipos de celdas
Define los tipos compartidos para filas leidas de Google Sheets.
"""

CellValue = str | int | float | bool | None

SheetRow = dict[str, CellValue]
