# Eduflex — Microservicios (despliegue en Kubuntu)

Arquitectura de microservicios del sistema de gestión académica Eduflex: 3 APIs de
dominio (usuarios, cursos, matrículas), un servicio de reportes alimentado por eventos,
un BFF/webapp, un reverse proxy por dominio, y RabbitMQ como message broker.

## Estructura

```
Contenedores/
├── reverse_proxy/       # nginx-proxy, enruta *.lms.local -> el contenedor correcto
├── micro_dbs/           # 4 Postgres (user, courses, enrollments, reports) + schema.sql de cada uno
├── message_broker/      # RabbitMQ (exchange "eduflex.events")
├── micro_webapp/        # las 4 APIs (FastAPI): user, courses, enrollments, reports + su worker
├── micro_bff_app/       # webapp Flask (BFF), único punto de entrada para el usuario final
└── levantar_todo.sh     # levanta todo en el orden correcto
```

Cada carpeta de primer nivel es un proyecto de `docker compose` independiente. Todas
comparten la misma red Docker (`ADSL`), así que se resuelven entre sí por el nombre del
servicio (`micro_db_user`, `micro_app_courses`, `rabbitmq`, etc.), sin depender de IPs.

## Requisitos previos

1. **Docker Engine + plugin de Compose** (no hace falta Docker Desktop en Linux):
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose-plugin
   sudo usermod -aG docker $USER
   ```
   Cierra sesión y vuelve a entrar (o `newgrp docker`) para que el cambio de grupo tome
   efecto sin necesitar `sudo` en cada comando.

2. Verifica que quedó instalado:
   ```bash
   docker --version
   docker compose version
   ```

## Si en esta máquina ya corre el monolito EduFlex

Si ya desplegaste el monolito siguiendo `B_Guia_Practica_Dockers_Monolitico.pdf`, esta
máquina **ya tiene** la red `ADSL` y un reverse proxy (`nginx-proxy` + `dnsmasq`)
sirviendo `mono.lms.local`. No hay que crear una segunda instancia de ninguno de los
dos — solo un proceso puede escuchar el puerto 80, y la red debe ser una sola para que
todo se resuelva por nombre de servicio.

Verifica lo que ya existe antes de levantar nada:
```bash
docker network ls | grep ADSL              # deberia listar la red ya creada
docker ps | grep nginx-proxy               # el reverse proxy del monolito
```

`levantar_todo.sh` ya detecta esto automáticamente: si encuentra un contenedor con
imagen `nginx-proxy` corriendo, **no** levanta el `reverse_proxy/` de esta carpeta, y
si la red `ADSL` ya existe, tampoco intenta crearla de nuevo — solo conecta los
microservicios nuevos a lo que ya está.

Lo único que falta verificar es el DNS: si el `dnsmasq` del monolito ya resuelve
`*.lms.local` como comodín, los nuevos dominios (`users.lms.local`,
`courses.lms.local`, etc.) van a funcionar solos. Si en cambio resuelve nombres
puntuales, hay que agregar los 5 nuevos a esa configuración (o al hosts file, ver
abajo) además del `mono.lms.local` que ya tenía.

## Resolución de dominios (`*.lms.local`)

El proyecto usa dominios locales para separar cada servicio (`users.lms.local`,
`courses.lms.local`, `enrollments.lms.local`, `reports.lms.local`, `micro.lms.local`).
En Kubuntu, la forma más simple es agregarlos al hosts file:

```bash
sudo tee -a /etc/hosts > /dev/null <<'EOF'

# Eduflex microservicios
127.0.0.1 mono.lms.local
127.0.0.1 users.lms.local
127.0.0.1 courses.lms.local
127.0.0.1 enrollments.lms.local
127.0.0.1 micro.lms.local
127.0.0.1 reports.lms.local
EOF
```

> Alternativa: si prefieres reproducir el diseño original de la guía (dnsmasq +
> systemd-resolved para DNS local), es totalmente viable en Kubuntu porque ahí sí
> existen ambos componentes — no fue necesario aquí porque el hosts file alcanza para
> este propósito.

## Levantar todo

Con Docker ya instalado y el hosts file configurado:

```bash
cd Contenedores
chmod +x levantar_todo.sh
./levantar_todo.sh
```

Esto crea la red `ADSL` (si no existe ya) y levanta, en orden, `reverse_proxy` →
`micro_dbs` → `message_broker` → `micro_webapp` (con build) → `micro_bff_app` (con
build) — saltándose la red y el reverse proxy si detecta que ya existen (por ejemplo,
por el monolito).

Si prefieres hacerlo a mano, en este orden (omite el `docker network create` y el
`reverse_proxy` si ya existen):
```bash
docker network create --driver bridge ADSL --subnet=172.30.0.0/16   # solo si no existe

cd reverse_proxy      && docker compose up -d                        # solo si no hay uno corriendo
cd ../micro_dbs        && docker compose up -d
cd ../message_broker   && docker compose up -d
cd ../micro_webapp     && docker compose up -d --build
cd ../micro_bff_app    && docker compose up -d --build
```

## Verificación

```bash
docker ps                                   # deben verse ~13 contenedores "Up"
curl -I http://users.lms.local/docs         # 200
curl -I http://micro.lms.local/login        # 200
```

Abre `http://micro.lms.local` en el navegador para usar la webapp, y
`http://localhost:15672` (usuario `eduflex` / clave `eduflexRabbit1`) para ver la
consola de RabbitMQ.

## Puertos a verificar si ya hay otras cosas corriendo

Antes de levantar, confirma que estos puertos estén libres en el host (o identifica
qué los usa, si es el propio monolito):

```bash
sudo ss -lntp | grep -E ":80|:5432|:5433|:5434|:5435|:5436|:5672|:15672"
```

`micro_dbs` publica en 5433-5436 (a propósito, para no chocar con un Postgres del
monolito que normalmente usaría 5432). Si el monolito sí publica algo en esos rangos,
hay que ajustar los puertos en `micro_dbs/docker-compose.yml` antes de levantarlo.

## Notas importantes

- **Las bases de datos arrancan vacías.** `schema.sql` crea las tablas, pero los datos
  de prueba (usuarios, cursos, matrículas) no viajan con el repositorio — hay que
  registrar usuarios de nuevo o restaurar un `pg_dump` si se exportó antes de migrar.
- **Credenciales de desarrollo, no de producción.** Las contraseñas en los
  `docker-compose.yml` (Postgres, RabbitMQ, `SECRET_KEY`) están en texto plano a
  propósito, pensadas solo para este entorno de práctica local.
- **`levantar_todo.sh` vs `levantar_todo.ps1`**: el `.ps1` es específico de Windows
  PowerShell y no corre en Kubuntu. El `.sh` de esta carpeta es su equivalente para
  Linux; usa uno u otro según el sistema operativo donde estés desplegando.
