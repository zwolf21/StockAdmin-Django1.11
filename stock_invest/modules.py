from collections import OrderedDict
from datetime import date, datetime, timedelta

from django.db.models import Q
from django.http import HttpResponse
from recordlib import RecordParser

from .models import Invest, InvestItem
from info.models import Info, invest_class_choices
from StockAdmin.services.FKHIS.opstock import get_opstock_object_list
from StockAdmin.services.FKHIS.db import EXCEPT_CODES


def gen_invest_list(invest, request):
	invests = {'po': '경구', 'in': '주사', 'de':'외용', 'fr': '냉장', 'op': '마약류'}
	invest_classes = [invests[key] for key in invests if request.get(key)]
	itemList = request.get('itemList', '').split(',\r\n')
	invest_items = Info.objects.filter(Q(invest_class__in=invest_classes)|Q(name__in=itemList))
	for drug in invest_items:
		item = InvestItem.objects.create(drug=drug, invest=invest)
	return invest

def report_excel_response(invset_slugs):
	records = []
	invests = Invest.objects.filter(slug__in=invset_slugs)
	for invest in invests:
		for item in invest.investitem_set.all():
			records.append({
						'EDI코드': item.drug.edi, '판매사': item.drug.firm, '약품명': item.drug.name_as, '실사량': item.total, '규격단위': item.drug.standard_unit,
						 '재고단가': item.price, '재고구분': item.drug.invest_class, '유효기한': item.expire
					})
	recs = RecordParser(records)
	recs = recs.select(['EDI코드', '판매사', '약품명', '실사량', '규격단위', '재고단가', '재고구분', '유효기한'])
	output = recs.to_excel()
	filename = '{}.xlsx'.format(' '.join(invset_slugs))
	response = HttpResponse(output, content_type='application/vnd.ms-excel')
	response['Content-Disposition'] = 'attachment; filename='+ filename
	return response


# object_list = get_opstock_object_list(today, psy, narc)

def sync_op_stock(invest_slug):
	today = date.today().strftime('%Y-%m-%d')
	records = get_opstock_object_list(today, True, False, drop_if = lambda row: row['drug_cd'] not in EXCEPT_CODES)
	invest = Invest.objects.get(slug=invest_slug)
	for item in invest.investitem_set.all():
		for row in records:
			if item.drug.code == row['drug_cd']:
				item.doc_amount = row['stock']
				item.save()
				break
		# item.doc_amount = records.get_first(where=lambda row: row['drug_cd'] == item.drug.code, 'drug_cd') or 0
		# item.save()

