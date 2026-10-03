from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.data.prepare_dataset import combine_text


class ClassifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="", max_length=500)
    content: str = Field(default="", max_length=100000)

    @model_validator(mode="after")
    def validate_text(self):
        combine_text(self.title, self.content)
        return self


class SaveArticleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prediction_id: str = Field(min_length=1, max_length=36)
    final_category: str = Field(min_length=1, max_length=100)
    confirmed: bool
