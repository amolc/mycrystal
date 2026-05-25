from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404
from .forms import BraceletForm
from .models import Bracelet, CartItem
from .image_mapping import load_bracelet_image_map

bracelet_image_map = load_bracelet_image_map()


def is_site_admin(user):
    return user.is_authenticated and user.username == 'admin'


def landing_page(request):
    bracelet_list = Bracelet.objects.order_by('-created_at')
    paginator = Paginator(bracelet_list, 9)
    page = request.GET.get('page')
    try:
        bracelets = paginator.page(page)
    except PageNotAnInteger:
        bracelets = paginator.page(1)
    except EmptyPage:
        bracelets = paginator.page(paginator.num_pages)

    for bracelet in bracelets:
        bracelet.local_image = bracelet_image_map.get(bracelet.name)
    return render(request, 'bracelets/landing.html', {'bracelets': bracelets})


def bracelets_list(request):
    qs = Bracelet.objects.all()

    q = request.GET.get('q', '').strip()
    material = request.GET.get('material', '').strip()
    color = request.GET.get('color', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    in_stock = request.GET.get('in_stock', '').strip()
    sort = request.GET.get('sort', 'new').strip()

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if material:
        qs = qs.filter(material__iexact=material)
    if color:
        qs = qs.filter(color__iexact=color)
    if min_price:
        try:
            qs = qs.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            qs = qs.filter(price__lte=float(max_price))
        except ValueError:
            pass
    if in_stock:
        if in_stock.lower() in ['1', 'true', 'yes', 'on']:
            qs = qs.filter(stock__gt=0)

    sort_map = {
        'new': '-created_at',
        'price_asc': 'price',
        'price_desc': '-price',
        'name_asc': 'name',
        'name_desc': '-name'
    }
    if sort not in sort_map:
        sort = 'new'
    order = sort_map[sort]
    qs = qs.order_by(order)

    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    try:
        bracelets = paginator.page(page)
    except PageNotAnInteger:
        bracelets = paginator.page(1)
    except EmptyPage:
        bracelets = paginator.page(paginator.num_pages)

    for bracelet in bracelets:
        bracelet.local_image = bracelet_image_map.get(bracelet.name)

    materials = Bracelet.objects.exclude(material='').values_list('material', flat=True).distinct().order_by('material')
    colors = Bracelet.objects.exclude(color='').values_list('color', flat=True).distinct().order_by('color')
    current_filters = {
        key: value
        for key, value in request.GET.dict().items()
        if key != 'page' and value
    }

    return render(request, 'bracelets/bracelets_list.html', {
        'bracelets': bracelets,
        'materials': materials,
        'colors': colors,
        'current_filters': current_filters,
        'selected_sort': sort or 'new',
    })


def bracelet_detail(request, pk):
    bracelet = get_object_or_404(Bracelet, pk=pk)
    bracelet.local_image = bracelet_image_map.get(bracelet.name)
    return render(request, 'bracelets/bracelet_detail.html', {'bracelet': bracelet})


@login_required(login_url='login_admin')
@user_passes_test(is_site_admin, login_url='login_admin')
def admin_dashboard(request):
    bracelets = Bracelet.objects.order_by('-created_at')
    for bracelet in bracelets:
        bracelet.local_image = bracelet_image_map.get(bracelet.name)
    return render(request, 'bracelets/admin_dashboard.html', {'bracelets': bracelets})


@login_required(login_url='login_admin')
@user_passes_test(is_site_admin, login_url='login_admin')
def create_bracelet(request):
    if request.method == 'POST':
        form = BraceletForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')
    else:
        form = BraceletForm()
    return render(request, 'bracelets/bracelet_form.html', {'form': form, 'title': 'Add Bracelet'})


@login_required(login_url='login_admin')
@user_passes_test(is_site_admin, login_url='login_admin')
def update_bracelet(request, pk):
    bracelet = get_object_or_404(Bracelet, pk=pk)
    if request.method == 'POST':
        form = BraceletForm(request.POST, request.FILES, instance=bracelet)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')
    else:
        form = BraceletForm(instance=bracelet)
    return render(request, 'bracelets/bracelet_form.html', {'form': form, 'title': 'Edit Bracelet'})


@login_required(login_url='login_admin')
@user_passes_test(is_site_admin, login_url='login_admin')
def delete_bracelet(request, pk):
    bracelet = get_object_or_404(Bracelet, pk=pk)
    if request.method == 'POST':
        bracelet.delete()
        return redirect('admin_dashboard')
    return render(request, 'bracelets/bracelet_confirm_delete.html', {'bracelet': bracelet})


@login_required(login_url='login_admin')
def cart_view(request):
    items = list(
        CartItem.objects
        .select_related('bracelet')
        .filter(user=request.user)
    )
    for item in items:
        item.bracelet.local_image = bracelet_image_map.get(item.bracelet.name)
    total = sum(item.line_total for item in items)
    return render(request, 'bracelets/cart.html', {'cart_items': items, 'cart_total': total})


@login_required(login_url='login_admin')
def add_to_cart(request, pk):
    bracelet = get_object_or_404(Bracelet, pk=pk)

    item, created = CartItem.objects.get_or_create(
        user=request.user,
        bracelet=bracelet,
        defaults={'quantity': 1},
    )
    if not created:
        item.quantity += 1
        item.save(update_fields=['quantity', 'updated_at'])

    messages.success(request, f'{bracelet.name} was added to your cart.')
    next_url = request.POST.get('next') or request.GET.get('next')
    return redirect(next_url or 'cart')


@login_required(login_url='login_admin')
def remove_from_cart(request, pk):
    CartItem.objects.filter(user=request.user, pk=pk).delete()
    messages.success(request, 'Item removed from your cart.')
    return redirect('cart')
