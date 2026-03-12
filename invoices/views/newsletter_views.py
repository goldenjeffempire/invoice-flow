import csv
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET

from invoices.models import EmailCampaign, NewsletterSubscriber
from invoices.forms import CampaignForm

logger = logging.getLogger(__name__)


def _is_staff(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# ──────────────────────────────────────────────────────────────────────────────
# Subscriber Dashboard
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(_is_staff)
def newsletter_dashboard(request):
    qs = NewsletterSubscriber.objects.all()

    # Search
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q))

    # Status filter
    status = request.GET.get("status", "")
    if status in (NewsletterSubscriber.Status.ACTIVE, NewsletterSubscriber.Status.UNSUBSCRIBED):
        qs = qs.filter(status=status)

    # Source filter
    source = request.GET.get("source", "")
    if source:
        qs = qs.filter(source=source)

    # Pagination
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Stats
    total = NewsletterSubscriber.objects.count()
    active = NewsletterSubscriber.objects.filter(status=NewsletterSubscriber.Status.ACTIVE).count()
    unsubscribed = NewsletterSubscriber.objects.filter(status=NewsletterSubscriber.Status.UNSUBSCRIBED).count()
    now = timezone.now()
    new_this_month = NewsletterSubscriber.objects.filter(
        subscribed_at__gte=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ).count()
    new_last_7d = NewsletterSubscriber.objects.filter(
        subscribed_at__gte=now - timedelta(days=7)
    ).count()

    sources = (
        NewsletterSubscriber.objects.values_list("source", flat=True)
        .distinct()
        .order_by("source")
    )

    recent_campaigns = EmailCampaign.objects.order_by("-created_at")[:5]

    context = {
        "page_obj": page_obj,
        "q": q,
        "status_filter": status,
        "source_filter": source,
        "sources": sources,
        "stats": {
            "total": total,
            "active": active,
            "unsubscribed": unsubscribed,
            "new_this_month": new_this_month,
            "new_last_7d": new_last_7d,
        },
        "recent_campaigns": recent_campaigns,
    }
    return render(request, "pages/newsletter/dashboard.html", context)


# ──────────────────────────────────────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(_is_staff)
@require_GET
def subscriber_export_csv(request):
    qs = NewsletterSubscriber.objects.all()
    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)

    response = HttpResponse(content_type="text/csv")
    filename = f"newsletter_subscribers_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(["Email", "First Name", "Status", "Source", "Subscribed At", "Unsubscribed At"])
    for sub in qs.order_by("email"):
        writer.writerow([
            sub.email,
            sub.first_name,
            sub.status,
            sub.source,
            sub.subscribed_at.strftime("%Y-%m-%d %H:%M:%S") if sub.subscribed_at else "",
            sub.unsubscribed_at.strftime("%Y-%m-%d %H:%M:%S") if sub.unsubscribed_at else "",
        ])
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Unsubscribe (public, no auth required)
# ──────────────────────────────────────────────────────────────────────────────

def newsletter_unsubscribe(request, token):
    subscriber = get_object_or_404(NewsletterSubscriber, unsubscribe_token=token)
    if request.method == "POST":
        if subscriber.status == NewsletterSubscriber.Status.ACTIVE:
            subscriber.unsubscribe()
            messages.success(request, "You've been successfully unsubscribed.")
        else:
            messages.info(request, "You were already unsubscribed.")
        return redirect("invoices:newsletter_unsubscribe_done")

    return render(request, "pages/newsletter/unsubscribe.html", {"subscriber": subscriber})


def newsletter_unsubscribe_done(request):
    return render(request, "pages/newsletter/unsubscribe_done.html")


# ──────────────────────────────────────────────────────────────────────────────
# Campaigns
# ──────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(_is_staff)
def campaign_list(request):
    campaigns = EmailCampaign.objects.select_related("created_by").order_by("-created_at")
    paginator = Paginator(campaigns, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "pages/newsletter/campaign_list.html", {"page_obj": page_obj})


@login_required
@user_passes_test(_is_staff)
def campaign_create(request):
    if request.method == "POST":
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.save()
            messages.success(request, f'Campaign "{campaign.title}" created successfully.')
            return redirect("invoices:campaign_detail", pk=campaign.pk)
    else:
        form = CampaignForm()
    return render(request, "pages/newsletter/campaign_form.html", {"form": form, "action": "Create"})


@login_required
@user_passes_test(_is_staff)
def campaign_detail(request, pk):
    campaign = get_object_or_404(EmailCampaign, pk=pk)
    return render(request, "pages/newsletter/campaign_detail.html", {"campaign": campaign})


@login_required
@user_passes_test(_is_staff)
def campaign_edit(request, pk):
    campaign = get_object_or_404(EmailCampaign, pk=pk)
    if campaign.status == EmailCampaign.Status.SENT:
        messages.error(request, "Sent campaigns cannot be edited.")
        return redirect("invoices:campaign_detail", pk=campaign.pk)

    if request.method == "POST":
        form = CampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, "Campaign updated successfully.")
            return redirect("invoices:campaign_detail", pk=campaign.pk)
    else:
        form = CampaignForm(instance=campaign)
    return render(request, "pages/newsletter/campaign_form.html", {"form": form, "campaign": campaign, "action": "Edit"})


@login_required
@user_passes_test(_is_staff)
@require_POST
def campaign_delete(request, pk):
    campaign = get_object_or_404(EmailCampaign, pk=pk)
    if campaign.status == EmailCampaign.Status.SENT:
        messages.error(request, "Sent campaigns cannot be deleted.")
    else:
        title = campaign.title
        campaign.delete()
        messages.success(request, f'Campaign "{title}" deleted.')
    return redirect("invoices:campaign_list")


@login_required
@user_passes_test(_is_staff)
@require_POST
def subscriber_delete(request, pk):
    subscriber = get_object_or_404(NewsletterSubscriber, pk=pk)
    email = subscriber.email
    subscriber.delete()
    messages.success(request, f"{email} removed from subscribers.")
    return redirect("invoices:newsletter_dashboard")
