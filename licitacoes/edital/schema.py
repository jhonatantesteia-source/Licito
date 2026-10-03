from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date

class SourceReference(BaseModel):
    text: str = Field(..., description="The literal text snippet from the document")
    page: Optional[int] = Field(None, description="Page number where the text was found")
    file: str = Field(..., description="The filename")

class ItemSchema(BaseModel):
    id: str
    description: str
    unit: str
    quantity: float
    ceiling_price: float = Field(..., description="Preço teto unitário")
    brand_required: Optional[str] = None
    source: SourceReference

class DeadlineSchema(BaseModel):
    event: str
    date: Optional[str] = Field(None, description="YYYY-MM-DD format if found")
    description: Optional[str] = None
    source: SourceReference

class DocumentRequirement(BaseModel):
    name: str
    legal_basis: Optional[str] = None
    validity_days: Optional[int] = None
    required_for_all: bool = True
    source: SourceReference

class EditalSchema(BaseModel):
    # General Info
    organ: str = Field(..., description="Órgão promotor da licitação")
    modality: str = Field(..., description="Modalidade (ex: Pregão Eletrônico, Dispensa)")
    process_number: str = Field(..., description="Número do processo/edital")
    object: str = Field(..., description="Descrição resumida do objeto")
    judgment_criterion: str = Field(..., description="Critério de julgamento (ex: Menor Preço por Item)")

    # Dates and Deadlines
    deadlines: List[DeadlineSchema] = []

    # Restrictions
    me_epp_exclusive: bool = False
    simples_nacional_required: bool = False
    restrictions: List[str] = []

    # Requirements
    required_documents: List[DocumentRequirement] = []

    # Items
    items: List[ItemSchema] = []

    # Other
    payment_terms: Optional[str] = None
    penalties: Optional[str] = None

    # Metadata
    source_file: str
    extraction_date: date
