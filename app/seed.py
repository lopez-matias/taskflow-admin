from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import Comment, Department, Priority, Request, RequestCategory, RequestHistory, RequestStatus, User


def seed() -> None:
    with SessionLocal() as db:
        if (db.scalar(select(func.count(Department.id))) or 0) > 0:
            print("Existing data found; the seed made no changes.")
            return

        departments = [
            Department(name="Tecnología", color="#ff9d00"),
            Department(name="Personas", color="#e85d04"),
            Department(name="Operaciones", color="#111111"),
            Department(name="Finanzas", color="#ffd166"),
            Department(name="Comercial", color="#6c757d"),
        ]
        db.add_all(departments)
        db.flush()

        users = [
            User(name="Marina Suárez", email="marina@orangeflow.demo", role="Administradora", avatar_color="#ff9d00", department=departments[0]),
            User(name="Tomás Vidal", email="tomas@orangeflow.demo", role="Especialista IT", avatar_color="#111111", department=departments[0]),
            User(name="Camila Acosta", email="camila@orangeflow.demo", role="People Partner", avatar_color="#e85d04", department=departments[1]),
            User(name="Bruno Santos", email="bruno@orangeflow.demo", role="Coordinador", avatar_color="#343a40", department=departments[2]),
            User(name="Julia Méndez", email="julia@orangeflow.demo", role="Analista financiera", avatar_color="#f48c06", department=departments[3]),
            User(name="Mateo Silva", email="mateo@orangeflow.demo", role="Ejecutivo comercial", avatar_color="#6c757d", department=departments[4]),
        ]
        db.add_all(users)

        categories = [
            RequestCategory(name="Accesos y sistemas", icon="key", description="Usuarios, permisos y soporte de aplicaciones"),
            RequestCategory(name="Compras", icon="bag", description="Adquisiciones, cotizaciones y proveedores"),
            RequestCategory(name="Personas", icon="users", description="Altas, beneficios y gestiones del equipo"),
            RequestCategory(name="Infraestructura", icon="tool", description="Mantenimiento de espacios y equipos"),
            RequestCategory(name="Administración", icon="file", description="Pagos, contratos y documentación"),
        ]
        db.add_all(categories)
        db.flush()

        now = datetime.now(UTC)
        rows = [
            ("Renovar licencias de diseño", "Renovar las licencias antes del cierre para evitar interrupciones en las entregas.", 0, 4, 1, Priority.CRITICAL, RequestStatus.IN_PROGRESS, -1, -6),
            ("Alta de accesos para nueva analista", "Crear correo, acceso al ERP y permisos de las carpetas del área financiera.", 0, 3, 1, Priority.HIGH, RequestStatus.ASSIGNED, 1, -2),
            ("Reparar climatización de sala norte", "El equipo dejó de funcionar y la sala se utiliza para reuniones con clientes.", 3, 2, 3, Priority.HIGH, RequestStatus.BLOCKED, -3, -9),
            ("Cotizar mobiliario ergonómico", "Solicitar tres opciones de sillas regulables con garantía mínima de tres años.", 1, 1, 3, Priority.MEDIUM, RequestStatus.IN_PROGRESS, 6, -4),
            ("Actualizar cuenta de proveedor", "Validar la constancia bancaria y actualizar los datos antes del próximo pago.", 4, 3, 4, Priority.MEDIUM, RequestStatus.RESOLVED, 2, -11),
            ("Acceso al tablero comercial", "Habilitar permisos de lectura para las nuevas incorporaciones del equipo comercial.", 0, 4, None, Priority.LOW, RequestStatus.NEW, 8, -1),
            ("Procesar factura de telefonía", "Registrar la factura mensual antes del cierre contable de la semana.", 4, 2, 4, Priority.HIGH, RequestStatus.CLOSED, -2, -20),
            ("Coordinar taller de liderazgo", "Definir facilitador, agenda y sala para responsables de cada departamento.", 2, 1, 2, Priority.MEDIUM, RequestStatus.ASSIGNED, 14, -3),
            ("Comprar monitores para puestos híbridos", "Se necesitan cuatro monitores de 27 pulgadas con conexión USB-C.", 1, 0, 3, Priority.MEDIUM, RequestStatus.IN_PROGRESS, 5, -7),
            ("Revisar contrato marco anual", "Validar condiciones comerciales y legales antes de enviar el contrato a firma.", 4, 4, None, Priority.HIGH, RequestStatus.NEW, 3, -2),
            ("Configurar impresora de recepción", "Conectar el nuevo equipo a la red y crear los perfiles de impresión.", 0, 2, 1, Priority.LOW, RequestStatus.RESOLVED, -1, -13),
            ("Reponer insumos de cafetería", "Comprar café, té y vasos compostables para cubrir el consumo mensual.", 1, 2, 3, Priority.LOW, RequestStatus.ASSIGNED, 9, -5),
        ]
        requests: list[Request] = []
        for title, description, cat, dep, assignee, priority, status, due_days, created_days in rows:
            created_at = now + timedelta(days=created_days)
            resolved_at = created_at + timedelta(days=2) if status in {RequestStatus.RESOLVED, RequestStatus.CLOSED} else None
            request = Request(
                title=title,
                description=description,
                category=categories[cat],
                requesting_department=departments[dep],
                assigned_user=users[assignee] if assignee is not None else None,
                priority=priority,
                status=status,
                due_at=now + timedelta(days=due_days),
                created_at=created_at,
                updated_at=now - timedelta(hours=2),
                resolved_at=resolved_at,
            )
            db.add(request)
            requests.append(request)
        db.flush()

        for index, request in enumerate(requests):
            actor = users[index % len(users)]
            db.add(RequestHistory(request=request, actor=actor, action="created", new_value="Solicitud creada", created_at=request.created_at))
            if request.assigned_user_id:
                db.add(RequestHistory(request=request, actor=users[0], action="assigned", field="assigned_user_id", new_value=str(request.assigned_user_id), created_at=request.created_at + timedelta(hours=1)))
            if request.status not in {RequestStatus.NEW, RequestStatus.ASSIGNED}:
                db.add(RequestHistory(request=request, actor=request.assigned_user or users[0], action="status_changed", field="status", old_value="assigned", new_value=request.status.value, created_at=request.created_at + timedelta(days=1)))

        db.add_all([
            Comment(request=requests[0], author=users[1], body="La renovación quedó enviada a Compras. Esperamos confirmación durante el día.", created_at=now - timedelta(hours=3)),
            Comment(request=requests[2], author=users[3], body="El proveedor debe importar un repuesto; actualizo apenas confirme la fecha.", created_at=now - timedelta(days=1)),
            Comment(request=requests[3], author=users[2], body="Incluyamos una alternativa con soporte lumbar y garantía extendida.", created_at=now - timedelta(hours=19)),
        ])
        db.commit()
        print(f"Demo data ready: {len(departments)} departments, {len(users)} users, and {len(requests)} requests.")


if __name__ == "__main__":
    seed()
