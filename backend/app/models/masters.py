"""Master/lookup-table models: districts and their offices, demographic lookups, and
the silk-type/activity/product (STAP) production taxonomy."""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import UniqueConstraint, Text
from ._common import _uuid, _now

__all__ = ["Designation", 
    "District", "Lac", "DirectorateOffice", "FigSettings", "SericultureCircle",
    "Caste", "Religion", "EducationLevel", "LossReason", "InputSourceCategory", "InputSourceType",
    "SilkType", "Activity", "Product", "SilkTypeActivityProduct", "StapSourceType", "ConversionStandard",
]


class District(SQLModel, table=True):
    __tablename__ = "districts"
    id: str = Field(default_factory=_uuid, primary_key=True)
    district_name: str = Field(unique=True, max_length=80)
    state_name: str = Field(default="Assam", max_length=60)
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    office_name: Optional[str] = Field(default=None, max_length=160)
    office_address: Optional[str] = Field(default=None, sa_column=Column(Text))
    office_contact_no: Optional[str] = Field(default=None, max_length=15)
    officer_in_charge_name: Optional[str] = Field(default=None, max_length=120)


class Lac(SQLModel, table=True):
    """Legislative Assembly Constituency — what a Sericulture Circle is mapped to.

    Replaces the old Sub-division Office / CDC master: the Directorate does not work in
    terms of SDOs, and CDC offices only exist in some places, so the constituency is the
    one label that covers all of Assam uniformly."""
    __tablename__ = "lacs"
    id: str = Field(default_factory=_uuid, primary_key=True)
    district_id: str = Field(foreign_key="districts.id", index=True)
    lac_no: Optional[int] = None          # official 1–126 numbering
    lac_name: str = Field(max_length=160)
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("district_id", "lac_name"),)


class DirectorateOffice(SQLModel, table=True):
    __tablename__ = "directorate_office"
    id: str = Field(default_factory=_uuid, primary_key=True)
    office_name: str = Field(default="Directorate of Sericulture, Assam", max_length=160)
    office_address: Optional[str] = Field(default=None, sa_column=Column(Text))
    office_contact_no: Optional[str] = Field(default=None, max_length=15)
    officer_in_charge_name: Optional[str] = Field(default=None, max_length=120)
    updated_at: datetime = Field(default_factory=_now)


class FigSettings(SQLModel, table=True):
    __tablename__ = "fig_settings"
    id: str = Field(default_factory=_uuid, primary_key=True)
    min_members: int = Field(default=5)
    updated_at: datetime = Field(default_factory=_now)


class SericultureCircle(SQLModel, table=True):
    __tablename__ = "sericulture_circles"
    id: str = Field(default_factory=_uuid, primary_key=True)
    district_id: str = Field(foreign_key="districts.id", index=True)
    lac_id: Optional[str] = Field(default=None, foreign_key="lacs.id", index=True)
    circle_name: str = Field(max_length=80)
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    office_name: Optional[str] = Field(default=None, max_length=160)
    office_address: Optional[str] = Field(default=None, sa_column=Column(Text))
    office_contact_no: Optional[str] = Field(default=None, max_length=15)
    officer_in_charge_name: Optional[str] = Field(default=None, max_length=120)
    __table_args__ = (UniqueConstraint("district_id", "circle_name"),)


class Designation(SQLModel, table=True):
    """Departmental post held by a State or District Admin, e.g. "Assistant Director of
    Sericulture (ADS)".

    display_order sorts by seniority rather than alphabetically -- listing Assistant
    Director above Director would read as wrong in a government hierarchy.
    """
    __tablename__ = "designations"
    id: str = Field(default_factory=_uuid, primary_key=True)
    designation_name: str = Field(unique=True, max_length=120)
    display_order: int = 0
    is_active: bool = True


class Caste(SQLModel, table=True):
    __tablename__ = "castes"
    id: str = Field(default_factory=_uuid, primary_key=True)
    caste_name: str = Field(unique=True, max_length=40)
    is_active: bool = True


class Religion(SQLModel, table=True):
    __tablename__ = "religions"
    id: str = Field(default_factory=_uuid, primary_key=True)
    religion_name: str = Field(unique=True, max_length=40)
    is_active: bool = True


class EducationLevel(SQLModel, table=True):
    __tablename__ = "education_levels"
    id: str = Field(default_factory=_uuid, primary_key=True)
    education_level_name: str = Field(unique=True, max_length=50)
    is_active: bool = True


class LossReason(SQLModel, table=True):
    __tablename__ = "loss_reasons"
    id: str = Field(default_factory=_uuid, primary_key=True)
    reason_name: str = Field(unique=True, max_length=120)
    is_active: bool = True


class InputSourceCategory(SQLModel, table=True):
    """Groups Input Source Types by kind (e.g. Land Related, Produce Related) so a given
    Activity->Product INPUT mapping can be restricted to only the source types that make
    sense for it (a land-area input shouldn't offer 'Market Source', a produce input
    shouldn't offer 'Own Land')."""
    __tablename__ = "input_source_categories"
    id: str = Field(default_factory=_uuid, primary_key=True)
    category_name: str = Field(unique=True, max_length=60)
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)


class InputSourceType(SQLModel, table=True):
    __tablename__ = "input_source_types"
    id: str = Field(default_factory=_uuid, primary_key=True)
    source_name: str = Field(unique=True, max_length=60)
    category_id: str = Field(foreign_key="input_source_categories.id", index=True)
    requires_scheme: bool = False   # e.g. "Government Source" — FIG President must also pick a Scheme
    is_own_source: bool = False     # triggers the combined stock+cycle-output auto-fill in the submission form
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)


class SilkType(SQLModel, table=True):
    __tablename__ = "silk_types"
    id: str = Field(default_factory=_uuid, primary_key=True)
    silk_type_name: str = Field(unique=True, max_length=50)
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)


class Activity(SQLModel, table=True):
    __tablename__ = "activities"
    id: str = Field(default_factory=_uuid, primary_key=True)
    activity_name: str = Field(max_length=120)
    silk_type_id: str = Field(foreign_key="silk_types.id", index=True)
    step_no: int
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (
        UniqueConstraint("silk_type_id", "activity_name"),
        UniqueConstraint("silk_type_id", "step_no"),
    )


class Product(SQLModel, table=True):
    __tablename__ = "products"
    id: str = Field(default_factory=_uuid, primary_key=True)
    product_name: str = Field(unique=True, max_length=80)
    unit_of_measure: str = Field(max_length=30)
    silk_type_id: Optional[str] = Field(default=None, foreign_key="silk_types.id", index=True)
    default_source_category_id: Optional[str] = Field(default=None, foreign_key="input_source_categories.id", index=True)
    is_perishable: bool = False
    is_byproduct: bool = False
    show_in_dashboard: bool = True
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)


class SilkTypeActivityProduct(SQLModel, table=True):
    __tablename__ = "silk_type_activity_products"
    id: str = Field(default_factory=_uuid, primary_key=True)
    silk_type_id: str = Field(foreign_key="silk_types.id", index=True)
    activity_id: str = Field(foreign_key="activities.id", index=True)
    product_id: str = Field(foreign_key="products.id", index=True)
    role: str = Field(default="OUTPUT", max_length=10)  # "INPUT" | "OUTPUT"
    input_group: Optional[str] = Field(default=None, max_length=40)  # only meaningful when role == "INPUT"
    input_source_category_id: Optional[str] = Field(default=None, foreign_key="input_source_categories.id", index=True)  # only meaningful when role == "INPUT"
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("silk_type_id", "activity_id", "product_id", "role"),)


class StapSourceType(SQLModel, table=True):
    """Which Input Source Types are valid for a given STAP INPUT mapping — only meaningful
    when the referenced SilkTypeActivityProduct row has role == "INPUT"."""
    __tablename__ = "stap_source_types"
    id: str = Field(default_factory=_uuid, primary_key=True)
    stap_id: str = Field(foreign_key="silk_type_activity_products.id", index=True)
    source_type_id: str = Field(foreign_key="input_source_types.id", index=True)
    __table_args__ = (UniqueConstraint("stap_id", "source_type_id"),)


class ConversionStandard(SQLModel, table=True):
    """State-Admin-configured expected input->output conversion range, independent of any
    specific Activity/STAP mapping — lets an admin map straight from an early-stage input
    product to a late-stage output product (e.g. Eri Eggs (DFL) -> Eri Silk Yarn), skipping
    over whichever Activities sit in between. Used by the Yield View to show an "Expected"
    range next to each row's Actual output, computed as that row's input quantity times
    min_pct/max_pct — a sanity-check display, not a validation gate on submission.

    The admin enters standard_input_qty/output_min_qty/output_max_qty (in each product's own
    unit — e.g. "100 Eri Egg (DFL) -> 20-25 kg Eri Cocoon") rather than typing a percentage
    directly; min_pct/max_pct are derived from those three at write time by the router
    (production.py's create/update_conversion_standard) and kept as real stored columns so
    the Yield View's consuming code (services/yield_matrix.py) needs no changes at all."""
    __tablename__ = "conversion_standards"
    id: str = Field(default_factory=_uuid, primary_key=True)
    silk_type_id: str = Field(foreign_key="silk_types.id", index=True)
    input_product_id: str = Field(foreign_key="products.id", index=True)
    output_product_id: str = Field(foreign_key="products.id", index=True)
    standard_input_qty: float
    output_min_qty: float
    output_max_qty: float
    min_pct: float
    max_pct: float
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    __table_args__ = (UniqueConstraint("silk_type_id", "input_product_id", "output_product_id"),)
