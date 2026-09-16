from strands.models.bedrock import BedrockModel
from config import MODEL_ID


def load_model() -> BedrockModel:
    """Get Bedrock model client using IAM credentials."""
    return BedrockModel(model_id=MODEL_ID)
