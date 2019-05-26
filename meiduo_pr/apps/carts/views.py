from django.shortcuts import render
from django.views import View
from django.http.response import HttpResponseForbidden, JsonResponse
from django_redis import get_redis_connection

from goods import models
from meiduo_pr.utils.response_code import RETCODE

import json
import pickle
import base64


class CartsView(View):
    """购物车管理"""

    def post(self, request):
        """添加购物车"""
        # 获取参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)
        # 校验数据
        # 判断数据是否齐全
        if not all([sku_id, count]):
            return HttpResponseForbidden('缺少必传参数')
        # 判断sku_id是否存在
        try:
            models.SKU.objects.get(id=sku_id)
        except models.SKU.DoesNotExist:
            return HttpResponseForbidden('sku_id 不存在')
        # 判断count是否为数字
        try:
            count = int(count)
        except Exception:
            return HttpResponseForbidden('count不是整数')
        # 判断selected是否为bool
        if selected:
            if not isinstance(selected, bool):
                return HttpResponseForbidden('selected不是bool类型')
        # 判断用户是否登录
        # user = request.user
        if not request.user.is_authenticated:
            # 如果未登录使用cookie

            # 首先从cookie中获取参数
            cart_str = request.COOKIES.get('carts')
            # 判断购物车中是否已经有了要加入购物车的数据
            if cart_str:
                # 有的话，count++
                cart_str_bytes = cart_str.encode()
                cart_bytes = base64.b16decode(cart_str_bytes)
                cart_dict = pickle.loads(cart_bytes)
                # 没有的话，准备一个空的字典
            else:
                cart_dict = {}
            if sku_id in cart_dict:
                origin_count = cart_dict[sku_id][count]
                count += origin_count
            cart_dict[sku_id] = {
                'sku_id': sku_id,
                'count': count,
            }

            cookie_set_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            # 创建响应对象
            response = JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
            response.set_cookie('carts', cookie_set_str)
            return response

        else:
            # 实例化redis对象
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            # 添加数据到购物车
            pl.hincrby('carts_%s' % request.user.id, sku_id, count)
            # 添加selected状态
            if selected:
                pl.sadd('selected_%s' % selected, sku_id)
            pl.execute()
            return JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})

    def get(self, request):
        """展示购物车"""
        # 判断用户登录没有
        if request.user.is_authenticated:
            # 登录了就去查询redis中的数据

            # 建立redis链接对象
            redis_conn = get_redis_connection('carts')

            # 去redis中获取数据
            sku_id = redis_conn.get('sku_id')
            selected = redis_conn.get('selected')

            cart_dict = {}
            for sku_id, count in redis_conn.hgetall('carts_%s' % sku_id).items():
                    cart_dict[int(sku_id)] = {
                        'count': int(count),
                        'selected': sku_id in selected
                    }

        else:
            # 没登录就去查询cookie中的数据
            cart_str = request.COOKIES.get('carts')
            # 转换成字典
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

        # 渲染购物车
        sku_ids = cart_dict.keys()
        skus = models.SKU.objects.filter(id__in=sku_ids)
        cart_skus = []
        for sku in skus:
            cart_skus.append({
                'id': sku.id,
                'name': sku.name,
                'count': cart_dict.get(sku.id).get('count'),
                'selected': str(cart_dict.get(sku.id).get('selected')),  # 将True，转'True'，方便json解析
                'default_image_url': sku.default_image.url,
                'price': str(sku.price),  # 从Decimal('10.2')中取出'10.2'，方便json解析
                'amount': str(sku.price * cart_dict.get(sku.id).get('count')),
            })

        context = {
            'cart_skus': cart_skus,
        }
        return render(request, 'cart.html', context)




