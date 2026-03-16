"""
InvoiceFlow – Client Views (production rebuild)
"""
from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..models import Client, ClientNote, Estimate, Invoice

logger = logging.getLogger(__name__)


def _get_workspace(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "current_workspace", None) if profile else None


@login_required
def client_list(request):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    search = request.GET.get("q", "").strip()
    ordering = request.GET.get("ordering", "name")
    page_num = request.GET.get("page", 1)

    qs = Client.objects.filter(workspace=workspace).annotate(
        invoice_count=Count("invoices", distinct=True),
        paid_total=Sum(
            "invoices__amount_paid",
            filter=Q(invoices__status__in=["paid", "part_paid"]),
            distinct=False,
        ),
        outstanding=Sum(
            "invoices__amount_due",
            filter=Q(invoices__status__in=["sent", "viewed", "part_paid", "overdue"]),
            distinct=False,
        ),
    )

    if search:
        qs = qs.filter(
            Q(name__icontains=search) | Q(email__icontains=search) | Q(phone__icontains=search)
        )

    valid_orderings = ["name", "-name", "created_at", "-created_at", "-invoice_count", "-paid_total"]
    if ordering in valid_orderings:
        qs = qs.order_by(ordering)
    else:
        qs = qs.order_by("name")

    paginator = Paginator(qs, 25)
    clients_page = paginator.get_page(page_num)

    total_clients = Client.objects.filter(workspace=workspace).count()
    active_clients = Client.objects.filter(workspace=workspace).annotate(
        ic=Count("invoices")
    ).filter(ic__gt=0).count()

    stats = {
        "total": total_clients,
        "active": active_clients,
        "total_billed": Invoice.objects.filter(workspace=workspace).aggregate(t=Sum("total_amount"))["t"] or 0,
        "total_outstanding": Invoice.objects.filter(
            workspace=workspace, status__in=["sent", "viewed", "part_paid", "overdue"]
        ).aggregate(t=Sum("amount_due"))["t"] or 0,
    }

    return render(request, "pages/clients/list.html", {
        "clients": clients_page,
        "search_query": search,
        "ordering": ordering,
        "stats": stats,
        "page_title": "Clients",
    })


@login_required
def client_create(request):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()

        if not name:
            messages.error(request, "Client name is required.")
        elif not email:
            messages.error(request, "Email address is required.")
        elif Client.objects.filter(workspace=workspace, email__iexact=email).exists():
            messages.error(request, "A client with this email already exists.")
        else:
            client = Client.objects.create(
                workspace=workspace,
                name=name,
                email=email,
                phone=request.POST.get("phone", ""),
                billing_address=request.POST.get("billing_address", ""),
                billing_city=request.POST.get("billing_city", ""),
                billing_state=request.POST.get("billing_state", ""),
                billing_country=request.POST.get("billing_country", ""),
                billing_zip=request.POST.get("billing_zip", ""),
                currency=request.POST.get("currency", "USD"),
                tax_id=request.POST.get("tax_id", ""),
                discount_rate=request.POST.get("discount_rate") or 0,
                notes=request.POST.get("notes", ""),
                tags=request.POST.get("tags", ""),
            )
            messages.success(request, f"Client '{client.name}' created successfully.")
            next_url = request.GET.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("invoices:client_detail", client_id=client.id)

    return render(request, "pages/clients/form.html", {
        "client": None,
        "currencies": Invoice.CURRENCY_CHOICES,
        "page_title": "New Client",
        "is_create": True,
    })


@login_required
def client_edit(request, client_id):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    client = get_object_or_404(Client, id=client_id, workspace=workspace)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()

        if not name:
            messages.error(request, "Client name is required.")
        elif not email:
            messages.error(request, "Email address is required.")
        elif Client.objects.filter(workspace=workspace, email__iexact=email).exclude(id=client.id).exists():
            messages.error(request, "Another client with this email already exists.")
        else:
            client.name = name
            client.email = email
            client.phone = request.POST.get("phone", "")
            client.billing_address = request.POST.get("billing_address", "")
            client.billing_city = request.POST.get("billing_city", "")
            client.billing_state = request.POST.get("billing_state", "")
            client.billing_country = request.POST.get("billing_country", "")
            client.billing_zip = request.POST.get("billing_zip", "")
            client.currency = request.POST.get("currency", "USD")
            client.tax_id = request.POST.get("tax_id", "")
            client.discount_rate = request.POST.get("discount_rate") or 0
            client.notes = request.POST.get("notes", "")
            client.tags = request.POST.get("tags", "")
            client.save()
            messages.success(request, f"Client '{client.name}' updated successfully.")
            return redirect("invoices:client_detail", client_id=client.id)

    return render(request, "pages/clients/form.html", {
        "client": client,
        "currencies": Invoice.CURRENCY_CHOICES,
        "page_title": f"Edit — {client.name}",
        "is_create": False,
    })


@login_required
def client_detail(request, client_id):
    workspace = _get_workspace(request)
    if not workspace:
        return redirect("invoices:onboarding_router")

    client = get_object_or_404(Client, id=client_id, workspace=workspace)

    invoices = Invoice.objects.filter(client=client, workspace=workspace).order_by("-created_at")
    estimates = Estimate.objects.filter(client=client, workspace=workspace).order_by("-created_at")
    notes = ClientNote.objects.filter(client=client).select_related("user").order_by("-created_at")

    stats = invoices.aggregate(
        total_billed=Sum("total_amount"),
        total_paid=Sum("amount_paid"),
        total_due=Sum("amount_due", filter=Q(status__in=["sent", "viewed", "part_paid", "overdue"])),
    )

    if request.method == "POST" and request.POST.get("action") == "add_note":
        content = request.POST.get("note_content", "").strip()
        if content:
            ClientNote.objects.create(client=client, user=request.user, content=content)
            messages.success(request, "Note added.")
        return redirect("invoices:client_detail", client_id=client.id)

    tags_list = [t.strip() for t in client.tags.split(",") if t.strip()] if client.tags else []

    return render(request, "pages/clients/detail.html", {
        "client": client,
        "invoices": invoices[:10],
        "estimates": estimates[:10],
        "notes": notes,
        "stats": stats,
        "tags_list": tags_list,
        "invoice_count": invoices.count(),
        "estimate_count": estimates.count(),
        "page_title": client.name,
    })


@login_required
@require_POST
def client_delete(request, client_id):
    workspace = _get_workspace(request)
    client = get_object_or_404(Client, id=client_id, workspace=workspace)
    if Invoice.objects.filter(client=client).exists():
        messages.error(request, "Cannot delete a client with existing invoices.")
        return redirect("invoices:client_detail", client_id=client.id)
    name = client.name
    client.delete()
    messages.success(request, f"Client '{name}' deleted.")
    return redirect("invoices:client_list")


@login_required
def client_autocomplete(request):
    workspace = _get_workspace(request)
    if not workspace:
        return JsonResponse({"results": []})
    q = request.GET.get("q", "")
    clients = Client.objects.filter(workspace=workspace, name__icontains=q).values("id", "name", "email")[:10]
    return JsonResponse({"results": list(clients)})
