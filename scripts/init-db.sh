#!/bin/bash

-- Создание пользователей и баз данных
CREATE DATABASE galmart_main;
CREATE DATABASE galmart_analytics;

-- Создание пользователя для приложения
CREATE USER galmart_user WITH ENCRYPTED PASSWORD 'galmart_password';

-- Права для основной базы
GRANT ALL PRIVILEGES ON DATABASE galmart_main TO galmart_user;
\c galmart_main;
GRANT ALL ON SCHEMA public TO galmart_user;

-- Права для аналитической базы
\c postgres;
GRANT ALL PRIVILEGES ON DATABASE galmart_analytics TO galmart_user;
\c galmart_analytics;
GRANT ALL ON SCHEMA public TO galmart_user;

-- Настройки производительности
\c galmart_main;
ALTER DATABASE galmart_main SET timezone TO 'Asia/Almaty';

\c galmart_analytics;
ALTER DATABASE galmart_analytics SET timezone TO 'Asia/Almaty';
