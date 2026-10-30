"""Avisos y guardado: presentación anterior, tiempos y recuperación."""

import pytest

from tests.e2e.test_aer_executive import fixed_day as fixed_day
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
