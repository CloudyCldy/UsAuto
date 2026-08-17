# うさぎ Autos

### Sistema de Gestión y Análisis de うさぎ Autos

**Proyecto Académico de Análisis de Datos y Machine Learning**

---

## Idiomas

* [Español](#español)
* [日本語 / Japonés](#japonés)
* [English / Inglés](#english)

---

# Español

## Descripción del proyecto

**Agencia Automotriz** es un proyecto académico desarrollado para la gestión y análisis de información relacionada con una agencia automotriz.

El sistema utiliza **MongoDB** como base de datos NoSQL y combina Python, Flask, análisis de datos, visualización y técnicas de **Machine Learning** para procesar información relacionada con vehículos, clientes, ventas y comportamiento del negocio.

### Objetivos principales

* Gestionar información de vehículos.
* Gestionar información de clientes.
* Registrar y consultar información de ventas.
* Analizar datos de la agencia.
* Generar visualizaciones y estadísticas.
* Implementar modelos de Machine Learning.
* Identificar tendencias en las ventas.
* Utilizar MongoDB como sistema de almacenamiento NoSQL.

---

## Tecnologías utilizadas

| Tecnología                 | Uso                                      |
| -------------------------- | ---------------------------------------- |
| Python                     | Lenguaje principal de programación       |
| Flask                      | Framework para la aplicación web         |
| MongoDB                    | Base de datos NoSQL                      |
| Pandas                     | Análisis y procesamiento de datos        |
| Scikit-learn               | Machine Learning                         |
| Matplotlib                 | Visualización de datos                   |
| Seaborn                    | Visualización de datos                   |
| Python Virtual Environment | Administración del entorno de desarrollo |

---

## Requisitos

Antes de ejecutar el proyecto, asegúrate de tener instalado:

* Python 3.14 o superior recomendado.
* MongoDB.
* Windows PowerShell o Windows CMD.
* Git, opcional.

El proyecto utiliza objetos `datetime` con información de zona horaria, por lo que se recomienda utilizar una versión reciente de Python.

---

## Instalación

### 1. Clonar el repositorio

```powershell
git clone <REPOSITORY_URL>
cd agencia-automotriz
```

### 2. Crear el entorno virtual

#### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### Windows CMD

```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

Una vez activado el entorno virtual, la terminal debería mostrar algo similar a:

```text
(.venv) PS C:\...\agencia-automotriz>
```

### 3. Instalar las dependencias

Actualizar las herramientas de Python:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
```

Instalar las dependencias del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Configuración de la base de datos

El proyecto utiliza **MongoDB** como base de datos NoSQL.

Antes de ejecutar el Seeder, asegúrate de que MongoDB esté iniciado.

Desde la carpeta raíz del proyecto, ejecuta:

```powershell
.\.venv\Scripts\python.exe database/seed.py
```

El archivo `seed.py` se encarga de insertar los datos iniciales necesarios para las pruebas y el funcionamiento del sistema.

---

## Ejecutar la aplicación

Para iniciar la aplicación:

```powershell
.\.venv\Scripts\python.exe app.py
```

Si la aplicación se inicia correctamente, Flask mostrará una dirección local similar a:

```text
http://127.0.0.1:5000
```

Abre esta dirección en el navegador para acceder al sistema.

---

## Estructura del proyecto

```text
agencia-automotriz/
│
├── database/
│   └── seed.py
│
├── models/
│
├── routes/
│
├── templates/
│
├── static/
│
├── analysis/
│
├── ml/
│
├── app.py
├── requirements.txt
├── README.md
└── .venv/
```

La estructura puede variar dependiendo de la versión del proyecto.

---

## Inicio rápido

```text
1. Iniciar MongoDB
        |
        v
2. Crear y activar el entorno virtual
        |
        v
3. Instalar las dependencias
        |
        v
4. Ejecutar database/seed.py
        |
        v
5. Ejecutar app.py
        |
        v
6. Abrir la aplicación en el navegador
```

---

## Solución de problemas

### PowerShell no permite activar el entorno virtual

Si PowerShell bloquea el script de activación, ejecuta:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Después vuelve a ejecutar:

```powershell
.\.venv\Scripts\Activate.ps1
```

### `pip` no es reconocido

Utiliza directamente el Python del entorno virtual:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Problemas de conexión con MongoDB

Comprueba que:

1. MongoDB esté iniciado.
2. La configuración de conexión sea correcta.
3. MongoDB esté disponible antes de ejecutar `seed.py`.
4. El nombre de la base de datos coincida con la configuración del proyecto.
5. La cadena de conexión utilizada por la aplicación sea correcta.

---

## Entorno de desarrollo

| Elemento              | Configuración              |
| --------------------- | -------------------------- |
| Sistema operativo     | Windows                    |
| Python                | 3.14+                      |
| Backend               | Flask                      |
| Base de datos         | MongoDB                    |
| Tipo de base de datos | NoSQL                      |
| Análisis de datos     | Pandas                     |
| Machine Learning      | Scikit-learn               |
| Entorno               | Python Virtual Environment |

---

## Proyecto académico

Este proyecto integra diferentes áreas de desarrollo y análisis de datos:

```text
Gestión de Base de Datos
        |
        v
Desarrollo de Aplicaciones Web
        |
        v
Análisis de Datos
        |
        v
Visualización de Datos
        |
        v
Machine Learning
```

---

# Japonés

## プロジェクト概要

**Agencia Automotriz** は、自動車販売店に関連する情報を管理・分析するために開発された学術プロジェクトです。

本システムでは、**MongoDB** を NoSQL データベースとして使用し、Python、Flask、データ分析、データ可視化、Machine Learning 技術を組み合わせています。

### 主な目的

* 車両情報の管理
* 顧客情報の管理
* 販売情報の登録・参照
* 販売データの分析
* データの可視化
* Machine Learning モデルの実装
* 販売傾向の分析
* MongoDB を使用した NoSQL データ管理

---

## 使用技術

| 技術                         | 用途                  |
| -------------------------- | ------------------- |
| Python                     | メインプログラミング言語        |
| Flask                      | Web アプリケーションフレームワーク |
| MongoDB                    | NoSQL データベース        |
| Pandas                     | データ分析・処理            |
| Scikit-learn               | Machine Learning    |
| Matplotlib                 | データ可視化              |
| Seaborn                    | データ可視化              |
| Python Virtual Environment | 開発環境の管理             |

---

## 必要条件

プロジェクトを実行するには、以下の環境が必要です。

* Python 3.14 以降を推奨
* MongoDB
* Windows PowerShell または Windows CMD
* Git（任意）

このプロジェクトではタイムゾーン情報を持つ `datetime` オブジェクトを使用しています。そのため、最近の Python バージョンを使用することを推奨します。

---

## インストール

### 1. リポジトリを取得

```powershell
git clone <REPOSITORY_URL>
cd agencia-automotriz
```

### 2. 仮想環境を作成

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

### 3. 必要なライブラリをインストール

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
```

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## データベースのセットアップ

このプロジェクトでは **MongoDB** を NoSQL データベースとして使用します。

Seeder を実行する前に MongoDB が起動していることを確認してください。

プロジェクトのルートディレクトリから以下を実行します。

```powershell
.\.venv\Scripts\python.exe database/seed.py
```

`seed.py` は、開発およびテストに必要な初期データを MongoDB に登録します。

---

## アプリケーションの起動

以下のコマンドを実行します。

```powershell
.\.venv\Scripts\python.exe app.py
```

正常に起動すると、Flask は以下のようなローカルアドレスを表示します。

```text
http://127.0.0.1:5000
```

ブラウザで表示されたアドレスを開いてください。

---

## プロジェクト構成

```text
agencia-automotriz/
│
├── database/
│   └── seed.py
│
├── models/
│
├── routes/
│
├── templates/
│
├── static/
│
├── analysis/
│
├── ml/
│
├── app.py
├── requirements.txt
├── README.md
└── .venv/
```

実際の構成はプロジェクトのバージョンによって異なる場合があります。

---

## 基本的な実行手順

```text
1. MongoDB を起動
        |
        v
2. 仮想環境を作成・有効化
        |
        v
3. 必要なライブラリをインストール
        |
        v
4. database/seed.py を実行
        |
        v
5. app.py を実行
        |
        v
6. ブラウザからアクセス
```

---

## トラブルシューティング

### PowerShell で仮想環境を有効化できない場合

以下を実行してください。

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

その後、以下を実行します。

```powershell
.\.venv\Scripts\Activate.ps1
```

### `pip` が認識されない場合

以下のコマンドを使用してください。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### MongoDB に接続できない場合

以下を確認してください。

1. MongoDB が起動していること。
2. MongoDB の接続設定が正しいこと。
3. `seed.py` を実行する前に MongoDB が利用可能であること。
4. データベース名がプロジェクトの設定と一致していること。
5. アプリケーションの接続文字列が正しいこと。

---

# English

## Project Overview

**Agencia Automotriz** is an academic project developed to manage and analyze information related to an automotive dealership.

The system uses **MongoDB** as a NoSQL database and combines Python, Flask, data analysis, visualization, and Machine Learning technologies.

### Main Objectives

* Manage vehicle information.
* Manage customer information.
* Register and query sales information.
* Analyze dealership data.
* Generate data visualizations and statistics.
* Implement Machine Learning models.
* Identify sales trends.
* Use MongoDB as a NoSQL data storage system.

---

## Technologies

| Technology                 | Purpose                            |
| -------------------------- | ---------------------------------- |
| Python                     | Main programming language          |
| Flask                      | Web application framework          |
| MongoDB                    | NoSQL database                     |
| Pandas                     | Data analysis and processing       |
| Scikit-learn               | Machine Learning                   |
| Matplotlib                 | Data visualization                 |
| Seaborn                    | Data visualization                 |
| Python Virtual Environment | Development environment management |

---

## Requirements

Before running the project, make sure the following are installed:

* Python 3.14 or newer recommended.
* MongoDB.
* Windows PowerShell or Windows CMD.
* Git, optional.

The project uses timezone-aware `datetime` objects. Therefore, a recent Python version is recommended.

---

## Installation

### 1. Clone the repository

```powershell
git clone <REPOSITORY_URL>
cd agencia-automotriz
```

### 2. Create the virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

### 3. Install dependencies

Upgrade the Python package management tools:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
```

Install the project dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## Database Setup

The project uses **MongoDB** as its NoSQL database.

Make sure MongoDB is running before executing the database seeder.

From the project root directory, run:

```powershell
.\.venv\Scripts\python.exe database/seed.py
```

The `seed.py` script inserts the initial data required for development and testing.

---

## Running the Application

Start the application with:

```powershell
.\.venv\Scripts\python.exe app.py
```

If the application starts successfully, Flask will display a local address similar to:

```text
http://127.0.0.1:5000
```

Open this address in your web browser.

---

## Project Structure

```text
agencia-automotriz/
│
├── database/
│   └── seed.py
│
├── models/
│
├── routes/
│
├── templates/
│
├── static/
│
├── analysis/
│
├── ml/
│
├── app.py
├── requirements.txt
├── README.md
└── .venv/
```

The actual structure may vary depending on the project version.

---

## Quick Start

```text
1. Start MongoDB
        |
        v
2. Create and activate the virtual environment
        |
        v
3. Install the dependencies
        |
        v
4. Run database/seed.py
        |
        v
5. Run app.py
        |
        v
6. Open the application in your browser
```

---

## Troubleshooting

### PowerShell does not allow virtual environment activation

Run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

### `pip` is not recognized

Use the Python executable from the virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### MongoDB connection problems

Check the following:

1. MongoDB is running.
2. The MongoDB connection configuration is correct.
3. MongoDB is available before running `seed.py`.
4. The database name matches the project configuration.
5. The application's MongoDB connection string is correct.

---

## Development Environment

| Item             | Configuration              |
| ---------------- | -------------------------- |
| Operating System | Windows                    |
| Python           | 3.14+                      |
| Backend          | Flask                      |
| Database         | MongoDB                    |
| Database Type    | NoSQL                      |
| Data Analysis    | Pandas                     |
| Machine Learning | Scikit-learn               |
| Environment      | Python Virtual Environment |

---

## Academic Project

This project integrates several areas of software development and data analysis:

```text
Database Management
        |
        v
Web Application Development
        |
        v
Data Analysis
        |
        v
Data Visualization
        |
        v
Machine Learning
```

---

## Project Information

**Project:** Agencia Automotriz
**Type:** Academic Project
**Backend:** Python / Flask
**Database:** MongoDB
**Database Type:** NoSQL
**Data Analysis:** Pandas
**Machine Learning:** Scikit-learn
**Environment:** Python Virtual Environment

---

## License

This project was developed for academic and educational purposes.
