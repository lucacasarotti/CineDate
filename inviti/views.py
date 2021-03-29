from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Invito
from .forms import InvitoForm
from static import GeoList, GenreList, CinemaList, TipologiaList
from django import forms
import functools
import operator
from django.db.models import Q
from django_filters.views import FilterView
from .filters import InvitoFilter, InvitoFilterFormHelper
from django.http import JsonResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from inviti.api.serializers import InvitoSerializer
from datetime import datetime


def create_queryset(dict):
    query_string = ''
    for key in dict:
        if dict[key] == 'true' and key not in ['last_mod', 'page_no', 'type', 'csrfmiddlewaretoken']:
            query_string = key+' '+query_string
    query_string = query_string[:-1]

    argument_list = []
    fields = ['genere']

    for query in query_string.split(' '):
        for field in fields:
            argument_list.append(Q(**{field + '__icontains': query}))

    query_set = Invito.objects.filter(functools.reduce(operator.or_, argument_list)).order_by('data')
    return query_set


class ViewPaginatorMixin(object):
    min_limit = 1
    max_limit = 10

    def paginate(self, object_list, page=1, limit=10, **kwargs):
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (TypeError, ValueError):
            page = 1

        try:
            limit = int(limit)
            if limit < self.min_limit:
                limit = self.min_limit
            if limit > self.max_limit:
                limit = self.max_limit
        except (ValueError, TypeError):
            limit = self.max_limit

        paginator = Paginator(object_list, limit)
        try:
            objects = paginator.page(page)
        except PageNotAnInteger:
            objects = paginator.page(1)
        except EmptyPage:
            objects = paginator.page(paginator.num_pages)
        data = {
            'pages': paginator.num_pages,
            'previous_page': objects.has_previous() and objects.previous_page_number() or None,
            'next_page': objects.has_next() and objects.next_page_number() or None,
            'data': list(objects),
        }
        return data


def about(request):
    return render(request, 'inviti/about.html', {'title': 'About'})


# ---------------    LIST VIEWS    ---------------

def home(request):
    context = {
        'inviti': Invito.objects.all()
    }
    return render(request, 'inviti/home.html', context)



'''class InvitoListView(ListView):
    model = Invito
    template_name = 'inviti/home.html'
    context_object_name = 'inviti'
    ordering = ['-data_invito']
    paginate_by = 5'''


class InvitiHome(ViewPaginatorMixin, View):
    '''
    Classe di Homepage, visualizza tutti gli inviti futuri
    '''

    def get(self, request):
        inviti = Invito.objects.filter(data__gte=datetime.today()).order_by('data')
        serialized = InvitoSerializer(inviti, many=True)
        resources = self.paginate(serialized.data, limit=10)
        # print(resources)
        context = {'inviti': resources['data'], 'num_pages': resources['pages']}

        if request.is_ajax():
            page_no = request.GET.get('page_no')
            resources = self.paginate(serialized.data, page=page_no, limit=10)
            return JsonResponse({"resources": resources})

        return render(request, 'inviti/home.html', context=context)


class InvitiUtente(ViewPaginatorMixin, View):
    '''
    Classe per visualizzare tutti gli inviti di un utente
    '''

    def get(self, request, *args, **kwargs):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        inviti = Invito.objects.filter(utente=user).order_by('data')
        serialized = InvitoSerializer(inviti, many=True)
        resources = self.paginate(serialized.data, limit=5)
        context = {
            'inviti': resources['data'],
            'num_pages': resources['pages'],
            'inviti_utente': True,
            'results_count': inviti.count(),
            'username': user.username,
        }

        if request.is_ajax():
            page_no = request.GET.get('page_no')
            resources = self.paginate(serialized.data, page=page_no, limit=5)
            return JsonResponse({"resources": resources})

        return render(request, 'inviti/inviti_utente.html', context=context)


'''class UtenteInvitiListView(ListView):

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Invito.objects.filter(utente=user).order_by('data')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['inviti_utente'] = True
        return context'''


class PrenotazioniUtente(LoginRequiredMixin, UserPassesTestMixin, ViewPaginatorMixin, View):
    '''
    Classe per visualizzare tutti gli inviti di un utente
    '''

    def get(self, request, *args, **kwargs):
        inviti = Invito.objects.filter(Q(partecipanti__username=self.kwargs.get('username'))).order_by('data')
        serialized = InvitoSerializer(inviti, many=True)
        resources = self.paginate(serialized.data, limit=5)
        context = {
            'inviti': resources['data'],
            'num_pages': resources['pages'],
            'inviti_utente': False,
            'results_count': inviti.count(),
            'username': self.kwargs.get('username'),
        }

        if request.is_ajax():
            page_no = request.GET.get('page_no')
            resources = self.paginate(serialized.data, page=page_no, limit=5)
            return JsonResponse({"resources": resources})

        return render(request, 'inviti/prenotazioni_utente.html', context=context)

    def test_func(self):
        user_prenotazioni = get_object_or_404(User, username=self.kwargs.get('username'))
        if self.request.user == user_prenotazioni:
            return True
        return False


'''class UtentePrenotazioniListView2(LoginRequiredMixin, UserPassesTestMixin, ListView):
    
    model = Invito
    template_name = 'inviti/inviti_utente.html'
    context_object_name = 'inviti'
    paginate_by = 5

    def get_queryset(self):
        return Invito.objects.filter(Q(partecipanti__username=self.kwargs.get('username'))).order_by('data')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['inviti_utente'] = False
        return context

    def test_func(self):
        user_prenotazioni = get_object_or_404(User, username=self.kwargs.get('username'))
        if self.request.user == user_prenotazioni:
            return True
        return False'''


class InvitiGenere(ViewPaginatorMixin, View):
    '''
    Questa classe serve a visualizzare tutti i post di un genere
    '''

    def get(self, request, *args, **kwargs):
        inviti = Invito.objects.filter(Q(genere__contains=self.kwargs.get('genere'))).order_by('-data_invito')
        serialized = InvitoSerializer(inviti, many=True)
        resources = self.paginate(serialized.data, limit=5)
        context = {
            'inviti': resources['data'],
            'num_pages': resources['pages'],
            'results_count': inviti.count(),
            'genere': self.kwargs.get('genere'),
        }

        if request.is_ajax():
            page_no = request.GET.get('page_no')
            resources = self.paginate(serialized.data, page=page_no, limit=5)
            return JsonResponse({"resources": resources})

        return render(request, 'inviti/inviti_genere.html', context=context)


# ---------------    FILTER VIEWS    ---------------

class InvitiFilterView(FilterView):
    template_name = 'inviti/inviti_filter.html'
    filterset_class = InvitoFilter
    formhelper_class = InvitoFilterFormHelper
    paginate_by = 5
    context_object_name = 'inviti'
    ordering = ['data']

    def get_queryset(self):
        queryset = Invito.objects.all().order_by('data')
        self.filterset = self.filterset_class(self.request.GET, queryset=queryset)
        return self.filterset.qs.distinct()

    def get_filterset(self, filterset_class):
        kwargs = self.get_filterset_kwargs(filterset_class)
        filterset = filterset_class(**kwargs)
        filterset.form.helper = self.formhelper_class()
        return filterset


class GeneriFilterView(ViewPaginatorMixin, View):

    def get(self, request):
        if request.is_ajax():
            inviti = create_queryset(request.GET)
            serialized = InvitoSerializer(inviti, many=True)
            page_no = request.GET.get('page_no')
            resources = self.paginate(serialized.data, page=page_no, limit=10)
            #print(resources)
            return JsonResponse({"resources": resources})

        inviti = Invito.objects.all().order_by('data')
        serialized = InvitoSerializer(inviti, many=True)
        resources = self.paginate(serialized.data, limit=10)
        #print(resources)
        context = {'inviti': resources['data'], 'num_pages': resources['pages'], 'generi_list': GenreList.GenreList.generi_value_list, 'tipologie_list': TipologiaList.TipologiaList.tipologia_value_list,}

        return render(request, 'inviti/generi_filter.html', context=context)


# ---------------    DETAIL VIEWS    ---------------

class InvitoDetailView(DetailView):
    model = Invito
    context_object_name = 'invito'

    # template --> looks for <app>/<model>_<viewtype>.html

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invito = self.get_object()
        if invito.posti_rimasti != invito.limite_persone:
            context['partecipanti_attuali'] = invito.partecipanti.all()
        return context


# ---------------    CREATE VIEWS    ---------------

class InvitoCreateView(LoginRequiredMixin, CreateView):
    model = Invito
    form_class = InvitoForm
    # fields = ['tipologia', 'cinema', 'film', 'data', 'orario', 'limite_persone', 'genere', 'commento']

    def form_valid(self, form):
        form.instance.utente = self.request.user
        return super().form_valid(form)


# ---------------    UPDATE VIEWS    ---------------

class InvitoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Invito
    form_class = InvitoForm
    # fields = ['tipologia', 'cinema', 'film', 'data', 'orario', 'limite_persone', 'genere', 'commento']

    def form_valid(self, form):
        form.instance.utente = self.request.user
        return super().form_valid(form)

    def test_func(self):
        invito = self.get_object()
        if self.request.user == invito.utente:
            return True
        return False


class InvitoPartecipa(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Invito
    template_name = 'inviti/partecipa.html'
    fields = []

    def form_valid(self, form):
        redirect_url = super().form_valid(form)
        utente = self.request.user
        invito = self.get_object()
        invito.partecipanti.add(utente.id)
        invito.save()
        return redirect_url

    def test_func(self):
        invito = self.get_object()
        if self.request.user != invito.utente and invito.posti_rimasti > 0 and self.request.user not in invito.partecipanti.all():
            return True
        return False


class InvitoRimuoviPartecipa(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Invito
    template_name = 'inviti/rimuovi_partecipazione.html'
    fields = []

    def form_valid(self, form):
        redirect_url = super().form_valid(form)
        utente = self.request.user
        invito = self.get_object()
        invito.partecipanti.remove(utente.id)
        invito.save()
        return redirect_url

    def test_func(self):
        invito = self.get_object()
        if self.request.user != invito.utente and self.request.user in invito.partecipanti.all():
            return True
        return False


# ---------------    DELETE VIEWS    ---------------

class InvitoDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Invito
    context_object_name = 'invito'
    success_url = '/inviti/'

    def test_func(self):
        invito = self.get_object()
        if self.request.user == invito.utente:
            return True
        return False
