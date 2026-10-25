"""El almacén modular conserva la identidad usada por todos los callbacks."""

import pytest

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_project_detail_entry import project_detail as project_detail
from tests.e2e.test_project_tabs import enter

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("family", ["aer", "ixs"])
def test_browser_callbacks_share_the_module_owned_state(
    portal, project_detail, fixed_day, family
):
    enter(portal, project_detail[1 if family == "aer" else 0])
    result = portal.evaluate(
        """family => {
      const state=beeProjectState,env=projectSessionContext();
      const active=family==='aer'?aerDashboardData:ixsProyectoActual;
      const owned=state[family]===active;
      const cache=state.clientCache===ixsClienteAccionesCache;
      const metadata=state.metadata===mapaMetaProyectosDashboard;
      const panels=state.aerPlanningRange===aerPlanFiltroMes
        &&state.aerPlanningFilters===aerPlanTableFilters
        &&state.aerRecords===aerClockifyFiltro
        &&state.aerResourceSelection===aerEvalRecursoSeleccionado
        &&state.ixsPlanning===ixsPlanState
        &&state.ixsPlanningAzure===ixsPlanAzureState
        &&state.ixsAzure===ixsAzureState;
      const marker={id:'marker',seleccion:[]};
      env.aerAi(marker);
      const adapter=state.aerAi===marker;
      const clockify={proyectoId:'P',registros:[{id:'entry'}]};
      state.clockify=clockify;
      const getter=ixsClockifyState===clockify;
      const before=state.request;
      projectEntryContext().invalidatePrevious();
      return {owned,cache,metadata,panels,adapter,getter,
        sequence:state.request===before+1,
        aerTab:state.aerTab===aerTabActual,
        ixsTab:state.ixsTab===ixsTabActual};
    }""",
        family,
    )
    assert all(result.values()), result
