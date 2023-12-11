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
      EMAIL_FROM: noreply@hnshosting.au
      EMAIL_PASSWORD: supersecretemailpassword
      EMAIL_HOST: mail.woodburn.au
      EMAIL_PORT: 587
      EMAIL_USE_TLS: True
      HSD_API_KEY: supersecretkey
      HSD_IP: 10.2.1.15 # Set to your HSD IP
      HSD_PORT: 12037 # Only change if using a custom port (or regtest)
      HSD_WALLET_PORT: 12039 # Only change if using a custom port (or regtest)
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