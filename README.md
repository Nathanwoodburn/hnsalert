# HNS Alert


## Docker compose

```yaml
version: '3'
services:
  app:
    image: git.woodburn.au/nathanwoodburn/hnsalert:latest # for production
    # image: git.woodburn.au/nathanwoodburn/hnsalert:dev # for development
    ports:
      - "61495:5000"
    depends_on:
      - db
    environment:
      DB_HOST: db
      DB_USER: db_user
      DB_PASSWORD: db_password
      DB_NAME: alert_db
      WORKERS: 2 # number of workers to run (should be 2 * number of cores)

  db:
    image: linuxserver/mariadb:latest
    environment:
      MYSQL_ROOT_PASSWORD: your-root-password
      MYSQL_DATABASE: alert_db
      MYSQL_USER: db_user
      MYSQL_PASSWORD: db_password
    volumes:
      - db_data:/var/lib/mysql
volumes:
  db_data:
```