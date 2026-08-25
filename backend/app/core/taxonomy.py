"""Controlled Aikyra taxonomy for Problem DNA classification.

Single source of truth for domains, subdomains, keywords, solution areas and
expertise. Accessed only through the helper functions below so a future
database-backed taxonomy can replace these constants without touching
classifier or service logic.
"""

from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Subdomain:
    name: str
    keywords: tuple[str, ...]
    problem_type: str | None = None


@dataclass(frozen=True)
class Domain:
    key: str
    label: str
    keywords: tuple[str, ...]
    subdomains: tuple[Subdomain, ...] = ()
    solution_areas: tuple[str, ...] = ()
    expertise: tuple[str, ...] = ()
    problem_type: str | None = None


TAXONOMY: dict[str, Domain] = {
    domain.key: domain
    for domain in (
        Domain(
            key="education",
            label="Education",
            keywords=("school", "schools", "education", "students", "teacher",
                      "teachers", "classroom", "literacy", "dropout", "learning"),
            subdomains=(
                Subdomain("School Infrastructure", ("school building", "toilets school", "classroom"), "Infrastructure"),
                Subdomain("Learning Quality", ("learning", "literacy", "dropout", "quality of education"), "Education Quality"),
                Subdomain("Digital Learning", ("digital learning", "online classes", "e-learning"), "Digital Services"),
            ),
            solution_areas=("Digital learning platforms", "Teacher training", "School infrastructure improvement"),
            expertise=("Education", "Pedagogy", "Curriculum Design", "Civil Engineering"),
            problem_type="Education Quality",
        ),
        Domain(
            key="healthcare",
            label="Healthcare",
            keywords=("health", "hospital", "clinic", "patients", "medical",
                      "disease", "medicine", "doctors", "treatment", "vaccination", "nutrition"),
            subdomains=(
                Subdomain("Primary Care Access", ("primary health", "nearest hospital", "no doctor"), "Public Health"),
                Subdomain("Disease Prevention", ("disease", "outbreak", "vaccination", "hygiene"), "Public Health"),
                Subdomain("Maternal & Child Health", ("maternal", "pregnancy", "infant", "child health"), "Public Health"),
            ),
            solution_areas=("Telemedicine", "Primary care outreach", "Health monitoring"),
            expertise=("Public Health", "Medicine", "Biomedical Engineering", "Data Science"),
            problem_type="Public Health",
        ),
        Domain(
            key="agriculture",
            label="Agriculture",
            keywords=("farmer", "farmers", "farming", "crop", "crops", "soil",
                      "irrigation", "harvest", "agriculture", "agricultural", "pesticide", "seed"),
            subdomains=(
                Subdomain("Soil & Water Management", ("soil", "soil moisture", "irrigation"), "Agricultural Productivity"),
                Subdomain("Crop Health", ("pest", "pesticide", "crop failure", "disease crop"), "Agricultural Productivity"),
                Subdomain("Market Access", ("market price", "mandi", "middlemen"), "Rural Economy"),
            ),
            solution_areas=("IoT soil sensing", "Precision irrigation", "Agri-market platforms"),
            expertise=("Agricultural Engineering", "Agronomy", "IoT", "Data Science"),
            problem_type="Agricultural Productivity",
        ),
        Domain(
            key="water_sanitation",
            label="Water & Sanitation",
            keywords=("water", "drinking water", "contaminated", "borewell",
                      "borewells", "sanitation", "toilet", "toilets", "sewage",
                      "groundwater", "water supply", "potable"),
            subdomains=(
                Subdomain("Drinking Water Quality", ("contaminated", "potable", "water quality", "fluoride", "arsenic"), "Public Health"),
                Subdomain("Water Supply & Scarcity", ("water supply", "scarcity", "borewell", "dry", "shortage"), "Infrastructure"),
                Subdomain("Sanitation", ("sanitation", "toilet", "toilets", "sewage", "open defecation"), "Infrastructure"),
            ),
            solution_areas=("Water purification", "Water quality monitoring", "Low-cost sensing", "Community water infrastructure"),
            expertise=("Civil Engineering", "Environmental Engineering", "IoT", "Public Health", "Chemistry"),
            problem_type="Infrastructure",
        ),
        Domain(
            key="environment",
            label="Environment",
            keywords=("environment", "pollution", "air quality", "deforestation",
                      "climate", "tree", "forest", "noise pollution", "ecosystem"),
            subdomains=(
                Subdomain("Air Quality", ("air quality", "air pollution", "smog", "dust"), "Environmental Health"),
                Subdomain("Conservation", ("deforestation", "forest", "tree cover", "wildlife"), "Conservation"),
            ),
            solution_areas=("Environmental sensing networks", "Afforestation programs", "Pollution monitoring"),
            expertise=("Environmental Engineering", "Ecology", "IoT", "Remote Sensing"),
            problem_type="Environmental Health",
        ),
        Domain(
            key="energy",
            label="Energy",
            keywords=("electricity", "power", "power cuts", "solar", "energy",
                      "grid", "voltage", "transformer", "street light", "lighting"),
            subdomains=(
                Subdomain("Supply Reliability", ("power cuts", "outage", "grid", "transformer"), "Infrastructure"),
                Subdomain("Renewable Energy", ("solar", "renewable", "biomass"), "Clean Energy"),
                Subdomain("Public Lighting", ("street light", "street lights", "dark streets", "lighting"), "Infrastructure"),
            ),
            solution_areas=("Solar micro-grids", "Smart metering", "Energy-efficient lighting"),
            expertise=("Electrical Engineering", "Renewable Energy", "IoT", "Energy Policy"),
            problem_type="Infrastructure",
        ),
        Domain(
            key="rural_livelihoods",
            label="Rural Livelihoods",
            keywords=("livelihood", "unemployment", "employment", "income",
                      "artisan", "handicraft", "self help group", "migrant", "wages"),
            subdomains=(
                Subdomain("Skill Development", ("skill", "training", "vocational"), "Livelihood Generation"),
                Subdomain("Market Linkages", ("handicraft", "artisan", "sell", "buyers"), "Rural Economy"),
            ),
            solution_areas=("Skill training platforms", "E-commerce marketplaces", "Cooperative models"),
            expertise=("Rural Development", "Economics", "Social Work", "Entrepreneurship"),
            problem_type="Rural Economy",
        ),
        Domain(
            key="urban_development",
            label="Urban Development",
            keywords=("urban", "city", "municipal", "ward", "housing", "slum",
                      "footpath", "park", "building collapse", "congestion"),
            subdomains=(
                Subdomain("Housing & Slums", ("slum", "housing", "informal settlement"), "Urban Planning"),
                Subdomain("Public Spaces", ("park", "playground", "footpath", "public space"), "Urban Planning"),
            ),
            solution_areas=("Participatory planning tools", "Low-cost housing tech", "GIS mapping"),
            expertise=("Urban Planning", "Civil Engineering", "Architecture", "GIS"),
            problem_type="Urban Planning",
        ),
        Domain(
            key="accessibility",
            label="Accessibility",
            keywords=("disability", "disabled", "wheelchair", "visually impaired",
                      "hearing impaired", "accessibility", "divyang", "sign language"),
            subdomains=(
                Subdomain("Physical Accessibility", ("wheelchair", "ramp", "accessible"), "Inclusive Infrastructure"),
                Subdomain("Assistive Technology", ("screen reader", "sign language", "assistive", "braille"), "Inclusive Technology"),
            ),
            solution_areas=("Assistive devices", "Accessible infrastructure design", "Accessibility auditing"),
            expertise=("Assistive Technology", "Rehabilitation Engineering", "Universal Design"),
            problem_type="Inclusive Infrastructure",
        ),
        Domain(
            key="public_administration",
            label="Public Administration",
            keywords=("government office", "scheme", "beneficiary", "ration card",
                      "pension", "corruption", "grievance", "bureaucracy", "documents", "certificate"),
            subdomains=(
                Subdomain("Grievance Redressal", ("grievance", "complaint", "corruption"), "Governance"),
                Subdomain("Scheme Delivery", ("scheme", "beneficiary", "ration card", "pension"), "Governance"),
            ),
            solution_areas=("Grievance tracking systems", "Scheme eligibility tools", "Process digitization"),
            expertise=("Public Policy", "Software Engineering", "Data Science"),
            problem_type="Governance",
        ),
        Domain(
            key="infrastructure",
            label="Infrastructure",
            keywords=("road", "roads", "bridge", "drainage", "construction",
                      "infrastructure", "potholes", "culvert", "street"),
            subdomains=(
                Subdomain("Roads & Transport Infrastructure", ("road", "roads", "potholes", "bridge"), "Infrastructure"),
                Subdomain("Drainage & Flood Control", ("drainage", "waterlogging", "flood", "drains"), "Infrastructure"),
            ),
            solution_areas=("Low-cost road repair materials", "Flood sensing and alerts", "Infrastructure monitoring"),
            expertise=("Civil Engineering", "Structural Engineering", "Remote Sensing", "IoT"),
            problem_type="Infrastructure",
        ),
        Domain(
            key="transportation",
            label="Transportation",
            keywords=("transport", "bus", "traffic", "commute", "road safety",
                      "accident", "vehicles", "last mile", "public transport"),
            subdomains=(
                Subdomain("Road Safety", ("accident", "accidents", "road safety", "blackspot"), "Public Safety"),
                Subdomain("Public Transport Access", ("bus", "public transport", "last mile", "frequency"), "Mobility"),
            ),
            solution_areas=("Route optimization", "Road-safety analytics", "Demand-responsive transport"),
            expertise=("Transportation Engineering", "Data Science", "Urban Planning"),
            problem_type="Mobility",
        ),
        Domain(
            key="waste_management",
            label="Waste Management",
            keywords=("garbage", "waste", "trash", "dump", "landfill", "plastic",
                      "recycling", "segregation", "littering"),
            subdomains=(
                Subdomain("Collection & Segregation", ("collection", "segregation", "not collected"), "Waste Processing"),
                Subdomain("Plastic & Recycling", ("plastic", "recycling", "polythene"), "Waste Processing"),
            ),
            solution_areas=("Smart bins", "Waste segregation automation", "Recycling supply chains"),
            expertise=("Environmental Engineering", "Chemical Engineering", "IoT", "Material Science"),
            problem_type="Waste Processing",
        ),
        Domain(
            key="digital_services",
            label="Digital Services",
            keywords=("internet", "connectivity", "mobile network", "wifi",
                      "digital", "app", "online", "network coverage", "bandwidth"),
            subdomains=(
                Subdomain("Connectivity", ("internet", "network coverage", "connectivity", "signal"), "Digital Inclusion"),
                Subdomain("Digital Literacy", ("digital literacy", "cyber fraud", "online safety"), "Digital Inclusion"),
            ),
            solution_areas=("Community networks", "Digital literacy programs", "Low-bandwidth services"),
            expertise=("Software Engineering", "Networking", "Telecommunication"),
            problem_type="Digital Inclusion",
        ),
    )
}

URGENCY_LEVELS = ("low", "medium", "high", "critical")
GEOGRAPHIC_CONTEXTS = ("rural", "semi_urban", "urban")

STAKEHOLDER_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Farmers", ("farmer", "farmers", "farming")),
    ("Students", ("student", "students")),
    ("Children", ("child", "children")),
    ("Elderly People", ("elderly", "senior citizens", "old age")),
    ("Women", ("women",)),
    ("Patients", ("patient", "patients")),
    ("Persons with Disabilities", ("disability", "disabled", "wheelchair", "divyang")),
    ("Residents", ("residents", "villagers", "community", "people", "families", "households", "inhabitants")),
)


@lru_cache
def get_domain(key: str) -> Domain | None:
    return TAXONOMY.get(key)


@lru_cache
def domain_label(key: str | None) -> str | None:
    if key is None:
        return None
    domain = TAXONOMY.get(key)
    return domain.label if domain else None


def all_domains() -> list[Domain]:
    return list(TAXONOMY.values())
