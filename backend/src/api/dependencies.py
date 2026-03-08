from fastapi import Depends

from ..db.client import get_db
from ..services.company_service import CompanyService
from ..services.profile_service import ProfileService
from ..services.graph_service import GraphService
from ..services.orchestration_service import OrchestrationService


def get_company_service(db=Depends(get_db)) -> CompanyService:
    return CompanyService(db)


def get_profile_service(db=Depends(get_db)) -> ProfileService:
    return ProfileService(db)


def get_graph_service(db=Depends(get_db)) -> GraphService:
    return GraphService(db)


def get_orchestration_service(
    company_svc: CompanyService = Depends(get_company_service),
    profile_svc: ProfileService = Depends(get_profile_service),
    graph_svc: GraphService = Depends(get_graph_service),
) -> OrchestrationService:
    return OrchestrationService(company_svc, profile_svc, graph_svc)
