from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

tasks = []


def index(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        task = request.POST.get("task")
        tasks.append(task)
        return render(request, "partials/task_item.html", {"task": task})
    return render(request, "core/homepage.html", {"tasks": tasks})
