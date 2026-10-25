"""Avisos y guardado: presentación anterior, tiempos y recuperación."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import state
from tests.e2e.test_project_detail_entry import project_detail as project_detail
from tests.e2e.test_project_tabs import enter

pytestmark = pytest.mark.django_db(transaction=True)


def modal(page):
    page.evaluate("""() => {
      const back=document.createElement('div');back.id='aer-modal-back';
      back.className='aer-modal-back';
      const dialog=document.createElement('div');dialog.className='aer-modal';
      const title=document.createElement('h3');
      title.textContent='Guardar cambios';
      const actions=document.createElement('div');
      actions.className='aer-actions';
      const button=document.createElement('button');button.id='feedback-save';
      button.className='aer-btn primary';
      const icon=document.createElement('span');icon.textContent='✓';
      button.append(icon,document.createTextNode(' Guardar'));
      actions.append(button);dialog.append(title,actions);back.append(dialog);
      document.body.append(back);
    }""")


@pytest.mark.parametrize("variant", ["success", "error", "saving", "restored"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_feedback_matches_previous(
    portal, project_detail, fixed_day, variant, width
):
    portal.set_viewport_size({"width": width, "height": 1000})
    directory = (
        Path("tmp/migration/project_detail/feedback") / variant / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    snapshots = []
    for previous in [True, False]:
        enter(portal, project_detail[1], previous)
        if variant in {"saving", "restored"}:
            modal(portal)
            portal.evaluate(
                """variant => {
              const saver=_aerStartSaving(_aerPrimaryModalBtn());
              if(variant==='restored')saver.error('No se pudo guardar');
            }""",
                variant,
            )
            selector = "#aer-modal-back, #aer-modal-back *"
            if variant == "restored":
                expect(portal.locator("#feedback-save")).to_be_enabled()
            else:
                expect(portal.locator("#feedback-save")).to_be_disabled()
        else:
            portal.evaluate(
                "type=>_aerToast('Mensaje de prueba',type)", variant
            )
            expect(portal.locator(".aer-toast.show")).to_be_visible()
            # Let the original transition settle before comparing boxes.
            portal.wait_for_timeout(250)
            selector = ".aer-toast, .aer-toast *"
        portal.mouse.move(0, 0)
        snapshots.append(state(portal, selector))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert snapshots[0] == snapshots[1]


@pytest.mark.parametrize("previous", [True, False])
def test_notice_timing_and_text_are_preserved(
    portal, project_detail, fixed_day, previous
):
    enter(portal, project_detail[1], previous)
    result = portal.evaluate("""() => {
      const timer=window.setTimeout,frame=window.requestAnimationFrame,queue=[];
      window.setTimeout=(callback,ms)=>queue.push({callback,ms});
      window.requestAnimationFrame=callback=>callback();
      try {
        _aerToast('<b>Texto seguro</b>');
        const notice=document.querySelector('.aer-toast');
        const text=notice.textContent,safe=!notice.querySelector('b');
        const shown=notice.classList.contains('show'),duration=queue[0].ms;
        queue[0].callback();
        const hidden=!notice.classList.contains('show'),exit=queue[1].ms;
        queue[1].callback();
        return {text,safe,shown,hidden,duration,exit,
          removed:!notice.isConnected};
      } finally {window.setTimeout=timer;window.requestAnimationFrame=frame;}
    }""")
    assert result == {
        "text": "<b>Texto seguro</b>",
        "safe": True,
        "shown": True,
        "hidden": True,
        "duration": 1800,
        "exit": 220,
        "removed": True,
    }


def test_save_contract_primary_button_and_close(
    portal, project_detail, fixed_day
):
    enter(portal, project_detail[1])
    modal(portal)
    result = portal.evaluate("""() => {
      const missing=_aerStartSaving(null);missing.ok();missing.error('ignored');
      const noNotice=!document.querySelector('.aer-toast');
      const button=_aerPrimaryModalBtn(),original=button.outerHTML;
      const saver=_aerStartSaving(button,'Guardando evaluación...');
      saver.ok();
      const success=button.disabled&&button.classList.contains('saving');
      const notice=document.querySelector('.aer-toast').textContent;
      saver.error();const restored=button.outerHTML===original;
      const wide=document.createElement('div');wide.id='aer-modal-wide-back';
      document.body.append(wide);aerCerrarModal();aerCerrarModal();
      const separate=wide.isConnected
        &&!document.getElementById('aer-modal-back');
      aerCerrarModalWide();aerCerrarModalWide();
      return {noNotice,success,notice,restored,separate,
        closed:!wide.isConnected};
    }""")
    assert result == {
        "noNotice": True,
        "success": True,
        "notice": "Guardado correctamente",
        "restored": True,
        "separate": True,
        "closed": True,
    }
