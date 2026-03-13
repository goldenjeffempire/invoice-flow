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
    return redirect("invoices:campaign_list")
