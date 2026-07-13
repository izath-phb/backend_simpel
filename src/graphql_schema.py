import graphene
from .models import User as UserModel, Report as ReportModel

class UserType(graphene.ObjectType):
    id = graphene.String()
    name = graphene.String()
    email = graphene.String()
    role = graphene.String()
    rt = graphene.String()
    rw = graphene.String()
    is_verified = graphene.Boolean()

    def resolve_id(self, info):
        return str(self.id)

class ReportType(graphene.ObjectType):
    id = graphene.String()
    title = graphene.String()
    description = graphene.String()
    category = graphene.String()
    status = graphene.String()
    user_name = graphene.String()

    def resolve_id(self, info):
        return str(self.id)

    def resolve_user_name(self, info):
        if self.user_id:
            return self.user_id.name
        return "Unknown"

class Query(graphene.ObjectType):
    hello = graphene.String(name=graphene.String(default_value="stranger"))
    system_status = graphene.String()
    
    users = graphene.List(UserType, role=graphene.String())
    user = graphene.Field(UserType, id=graphene.String(required=True))
    
    reports = graphene.List(ReportType, status=graphene.String())
    report = graphene.Field(ReportType, id=graphene.String(required=True))

    def resolve_hello(self, info, name):
        return f'Hello {name}!'

    def resolve_system_status(self, info):
        return 'SIMPEL API - GraphQL Gateway is running smoothly with MongoDB.'

    def resolve_users(self, info, role=None):
        if role:
            return UserModel.objects(role=role)
        return UserModel.objects.all()
        
    def resolve_user(self, info, id):
        try:
            return UserModel.objects.get(id=id)
        except Exception:
            return None

    def resolve_reports(self, info, status=None):
        if status:
            return ReportModel.objects(status=status)
        return ReportModel.objects.all()

    def resolve_report(self, info, id):
        try:
            return ReportModel.objects.get(id=id)
        except Exception:
            return None

schema = graphene.Schema(query=Query)
