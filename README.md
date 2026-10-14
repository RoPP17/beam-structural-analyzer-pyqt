# 🌉 BeamAnalyzer — Calculadora y Suite de Análisis Estructural de Vigas

[![Python](https://img.shields.io/badge/Python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Architecture](https://img.shields.io/badge/Design%20Pattern-MVC%20Modular-orange?style=for-the-badge)](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller)
[![Engineering](https://img.shields.io/badge/Discipline-Resistencia%20de%20Materiales-blue?style=for-the-badge)](https://en.wikipedia.org/wiki/Strength_of_materials)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

> **Software de escritorio profesional para el análisis estático y cálculo estructural de vigas** desarrollado para la asignatura de **Resistencia de Materiales** en la **Universidad Técnica de Ambato (UTA)**.

---

## 🌟 Características Principales

* **📐 Tipología Completa de Apoyos Estructurales:**
  * Apoyos simples (rodillos / móviles).
  * Apoyos fijos articulados (pasadores).
  * Empotramientos rígidos con reacción de momento en cualquier punto de la viga.
* **⚡ Múltiples Configuraciones de Carga:**
  * Cargas puntuales concentradas en cualquier coordenada $x$.
  * Momentos flectores concentrados externos (horario / antihorario).
  * Cargas distribuidas rectangulares (uniformes).
  * Cargas distribuidas triangulares y trapezoidales con pendientes arbitrarias.
* **📈 Diagramas Estructurales Sincronizados:**
  * Diagrama de Fuerza Cortante $V(x)$ con identificación de cruces por cero.
  * Diagrama de Momento Flector $M(x)$ con cálculo del momento flector máximo absoluto $M_{\text{máx}}$.
  * Renderizado continuo de cotas dinámicas y cotas de sección.
* **🎨 Motor Gráfico Paramétrico de Dibujo:**
  * Renderizado vectorial nítido de la viga, apoyos, flechas de carga y acotaciones.
  * Soporte de temas visuales integrados: **Dark Engineering Theme** y **Clean Light Theme**.
* **📑 Reportes y Exportación Técnica:**
  * Generación de reportes detallados con el procedimiento estático paso a paso (equilibrio global $\sum F_y = 0$, $\sum M = 0$).

---

## 🏗️ Arquitectura Modular del Software (MVC)

El proyecto sigue una arquitectura desacoplada estricta:

```
BeamAnalyzer/
├── main.py                      # Punto de entrada de la aplicación PyQt5
├── requirements.txt             # Dependencias del proyecto
├── run.bat                      # Lanzador directo
│
├── app/
│   ├── core/                    # NÚCLEO MECÁNICO Y MATEMÁTICO
│   │   ├── loads.py             # Definición y funciones de corte/momento de cargas
│   │   ├── supports.py          # Condiciones de frontera de apoyos
│   │   └── units.py             # Conversión de unidades (SI / Imperial)
│   │
│   ├── controllers/             # CONTROLADORES DE APLICACIÓN
│   │   └── app_controller.py    # Coordinador entre UI, cálculo y render
│   │
│   ├── render/                  # PIPELINE DE RENDERIZADO VECTORIAL
│   │   ├── beam_renderer.py     # Dibujo del cuerpo de la viga y ejes neutros
│   │   ├── load_renderer.py     # Renderizado de flechas y gradientes de carga
│   │   ├── support_renderer.py  # Símbolos técnicos de apoyos y empotramientos
│   │   └── dimension_renderer.py# Cotas numéricas y líneas de extensión
│   │
│   ├── ui/                      # COMPONENTES DE INTERFAZ GRÁFICA
│   │   ├── beam_canvas.py       # Lienzo interactivo principal
│   │   ├── diagram_panel.py     # Paneles de gráficas V(x) y M(x)
│   │   ├── property_panel.py    # Panel lateral de propiedades de carga
│   │   ├── results_panel.py     # Tabla de reacciones y valores extremos
│   │   └── dialogs/             # Diálogos modales para agregar cargas y apoyos
│   │
│   └── assets/styles/           # Hojas de estilo QSS (Dark & Light)
│
└── docs/                        # Evidencias y memorias de cálculo
    └── Evidencia_Calculadora_Vigas.pdf
```

---

## 🚀 Instalación y Ejecución

```bash
# 1. Clonar el repositorio
git clone https://github.com/RoPP17/beam-structural-analyzer-pyqt.git
cd beam-structural-analyzer-pyqt

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar la aplicación
python main.py
```

---

## 👨‍💻 Autor

* **Roberto Andrés Pepe Sánchez** — Facultad de Ingeniería Civil y Mecánica, [Universidad Técnica de Ambato (UTA)](https://uta.edu.ec/)

## 📜 Licencia

Distribuido bajo la Licencia [MIT](LICENSE).

---

## 📚 Citación Académica (Citation)

Si utilizas este software o código en investigaciones, docencia o proyectos de ingeniería, por favor cítalo como:

``bibtex
@software{pepe_sanchez_2026_beam_analyzer,
  author       = {Pepe Sánchez, Roberto Andrés},
  title        = {beam-structural-analyzer-pyqt: Structural Analysis and Beam Deflection Solver with PyQt GUI},
  month        = oct,
  year         = 2026,
  publisher    = {Zenodo},
  version      = {v1.0.0},
  url          = {https://github.com/RoPP17/beam-structural-analyzer-pyqt}
}
``

También puedes citarlo automáticamente usando el botón **"Cite this repository"** en la barra lateral de GitHub o leyendo directamente el archivo [CITATION.cff](./CITATION.cff).
