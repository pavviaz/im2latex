<div id="top"></div>

<!-- PROJECT LOGO -->
<br />
<div align="center">

<img src="example_images/photo_2023-11-18_20-53-46-3.jpg" height=200 align = "center"/>

<h3 align="center">DeepScriptum</h3>

  <p align="center">
    Convert any PDF into it's LaTeX source
    <br />
    <a href="">View Demo</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#current-state-and-updates">Current state and updates</a>
    </li>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

<!-- UPDATES -->
## Current state and updates

This branch contains demo DeepScriptum implementation using VLLM and map-reduce approach to perfom OCR in parallel. The future work includes collecting big enough dataset to train my own VLLM and deploying web version with mobile/pc clients.


### June 2024:
Early demo implemented with GPT-4o. Includes FastAPI backend (Celery used for task managing) and Streamlit frontend.

<img src="example_images/cv_md.gif" height=400 align = "center"/>

### May 2024:
Deep dive into VLLMs, understanding how it work and how to use it for the project.


For more info please visit <a href="https://t.me/+MGclBt67OUhmNGEy">my Telegram page</a> (RU).

<!-- ABOUT THE PROJECT -->
## About The Project

The main idea of this project is to develop high accuracy LaTeX OCR for any input PDF. Such a markup gives user full control over his document, including precise copying of any block, like text, formulas, tables, etc., editing, deleting, moving them, etc. MVP includes neural worker (currently two-stage solution) for OCR performing, API to handle user requests, web interface for interaction and probably some DB's for data storing.

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- GETTING STARTED -->

### Installation

1) Git clone or download
2) Create .env file in root, it must contain these keys:
```
RABBITMQ_IP=amqp://<RABMQ_EXAMPLE_USR>:<RABMQ_EXAMPLE_PASSWD>@rabbitmq:5672/
REDIS_IP=redis://redis:6379/0

RABBITMQ_ERLANG_COOKIE=<RABMQ_EXAMPLE_COOKIE>
RABBITMQ_LOGIN=<RABMQ_EXAMPLE_USR>
RABBITMQ_PASSWD=<RABMQ_EXAMPLE_PASSWD

OPENAI_KEY=<YOUR_OPENAI_KEY>
```
3) `sudo docker-compose build && sudo docker-compose up`

Congrats! You can access your service on `http://localhost:8501`

<p align="right">(<a href="#top">back to top</a>)</p>


### Built With

* [FastAPI](https://fastapi.tiangolo.com/)
* [Celery](https://github.com/celery/celery)
* [Streamlit](https://streamlit.io/)
* [OpenAI GPT](https://openai.com/)

<p align="right">(<a href="#top">back to top</a>)</p>


<!-- CONTACT -->
## Authors

<a href="https://www.linkedin.com/in/pavviaz/">Vyaznikov Pavel</a>

<p align="right">(<a href="#top">back to top</a>)</p>