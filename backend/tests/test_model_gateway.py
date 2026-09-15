import pytest
from app.core.config import Settings
from app.infrastructure.llm.openai_compatible_gateway import ModelGatewayError,OpenAICompatibleGateway,_local_budget_cents

@pytest.mark.asyncio
async def test_daily_budget_stops_before_network_call():
    _local_budget_cents.clear();gateway=OpenAICompatibleGateway(Settings(model_daily_budget=0,model_max_cost_per_call=.5,training_task_store="memory"))
    with pytest.raises(ModelGatewayError) as error:await gateway._reserve_budget()
    assert error.value.code=="MODEL_BUDGET_EXCEEDED"
