# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import time

from osv import fields
from osv import osv
import pooler
import os
import base64
import tools

class dm_ddf_plugin(osv.osv):
    _name = "dm.ddf.plugin"

    def search(self, cr, uid, args, offset=0, limit=None, order=None,context=None, count=False):
        if 'template_id' in context:
            if not context['template_id']:
                return []
            res = self.pool.get('dm.document.template').browse(cr,uid,context['template_id'])
            plugin_ids = map(lambda x : x.id,res.plugin_ids)
            return plugin_ids
        return super(dm_ddf_plugin,self).search(cr,uid,args,offset,limit,order,context,count)
    
    def _check_plugin(self, cr, uid, ids=False, context={}):
        dm_document = self.pool.get('dm.offer.document')
#        offer_step = self.pool.get('dm.offer.step')
#        document_template = self.pool.get('dm.document_template')
        ddf_plugin = self.pool.get('dm.ddf.plugin')
        dm_customer_order = self.pool.get('dm.customer.order')
        
        document_ids = dm_document.search(cr,uid,[])
        documents = dm_document.browse(cr,uid,document_ids,['document_template_id','step_id'])

        for d in documents:
            order_id = dm_customer_order.search(cr,uid,[('offer_step_id','=',d.step_id.id)])
            order = dm_customer_order.browse(cr,uid,order_id)
            customer_id = map(lambda x:x.customer_id.id,order)
            plugins = d.document_template_id.plugin_ids
            for plugin in plugins:
                path = os.path.join(os.getcwd(), "addons/dm/dm_ddf_plugins",cr.dbname)
                plugin_name = plugin.file_fname.split('.')[0]
                import sys
                sys.path.append(path)
                X =  __import__(plugin_name)
                plugin_func = getattr(X,plugin_name)
                plugin_value = map(lambda x : (x,plugin_func(x),plugin.id),customer_id)
        return True
    
    def _data_get(self, cr, uid, ids, name, arg, context):
        result = {}
        cr.execute('select id,file_fname from dm_ddf_plugin where id in ('+','.join(map(str,ids))+')')
        
        for id ,r in cr.fetchall():            
            try:
                path = os.path.join(os.getcwd(), "addons/dm/dm_ddf_plugins",cr.dbname)
                value = file(os.path.join(path,r), 'rb').read()
                result[id] = base64.encodestring(value)
            except:
                result[id]=''
        return result

    def _data_set(self, cr, obj, id, name, value, uid=None, context={}):
        if not value:
            return True
        sql = "select file_fname from dm_ddf_plugin where id = %d"%id
        cr.execute(sql) 
        res = cr.fetchone()

        path = os.path.join(os.getcwd(), "addons/dm/dm_ddf_plugins",cr.dbname)
        if not os.path.isdir(path):
            os.makedirs(path)
        filename = res[0]
        fname = os.path.join(path, filename)
        fp = file(fname,'wb')
        v = base64.decodestring(value)
        fp.write(v)
        return True
    
    _columns = {
        'name' : fields.char('DDF Plugin Name', size=64),
        'file_id': fields.function(_data_get,method=True,fnct_inv=_data_set,string='File Content',type="binary"),
        'file_fname': fields.char('Filename',size=64),
     }
dm_ddf_plugin()

class dm_document_template(osv.osv):
    _name = "dm.document.template"
    _columns = {
        'name' : fields.char('Template Name', size=128),
        'dynamic_fields' : fields.many2many('ir.model.fields','dm_template_fields','template_field_id','template_id','Fields',domain=[('model','like','dm.%')]),
        'plugin_ids' : fields.many2many('dm.ddf.plugin','dm_template_plugin_rel','dm_ddf_plugin_id','dm_document_template_id', 'Plugin'),
        }
    
    def write(self, cr, uid, ids, vals, context=None):
        res = super(dm_document_template,self).write(cr, uid, ids, vals, context)
        document_template =self.read(cr,uid,ids)[0]
        list1 = document_template['dynamic_fields']
        dm_offer_document = self.pool.get('dm.offer.document')
        document_ids = dm_offer_document.search(cr,uid,[('document_template_id','=',ids[0])])
        documents = dm_offer_document.read(cr,uid,document_ids)
        for doc in documents:
            list2 = doc['document_template_field_ids'] 
            diff = list(set(list2).difference(set(list1)))
            map(lambda x : list2.remove(x) ,diff)
            dm_offer_document.write(cr,uid,doc['id'],{'document_template_field_ids':[[6, 0,list2]]})
        return res                 
dm_document_template()

class dm_customer_plugin(osv.osv):
    _name = "dm.customer.plugin"
    _columns = {
        'customer_id' : fields.many2one('dm.customer', 'Customer Name'),
        'plugin_id' : fields.many2one('dm.ddf.plugin', 'Plugin'),
        'value' : fields.char('Value', size=64),
        'date' : fields.date('Date'),
    }
    
dm_customer_plugin()
