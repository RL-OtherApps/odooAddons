# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
#
#
#    Author : Smerghetto Daniel  (Omniasolutions)
#    mail:daniel.smerghetto@omniasolutions.eu
#    Copyright (c) 2018 Omniasolutions (http://www.omniasolutions.eu)
#    All Right Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

'''
Created on Dec 18, 2017

@author: daniel
'''
from odoo import models
from odoo import api
from odoo import fields
from odoo import _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    external_production = fields.Many2one('mrp.production')
    sub_contracting_operation = fields.Selection([('open', _('Open external Production')),
                                                  ('close', _('Close external Production'))])
    sub_production_id = fields.Integer(string=_('Sub production Id'))
    pick_out = fields.Many2one('stock.picking', string=_('Reference Stock pick out'))
    sub_workorder_id = fields.Integer(string=_('Sub Workorder Id'))

    @api.multi
    def do_new_transfer(self):
        res = super(StockPicking, self).do_new_transfer()
        if isinstance(res, dict) and 'view_mode' in res:    # In this case will be returned a wizard
            return res
        for objPick in self:
            self.commonSubcontracting(objPick)
        return res

    @api.multi
    def commonSubcontracting(self, objPick):
        purchase_order_line = self.env['purchase.order.line']
        if objPick.isIncoming(objPick):
            objProduction = objPick.env['mrp.production'].search([('id', '=', objPick.sub_production_id)])
            if objProduction and objProduction.state == 'external':
                if objProduction.isPicksInDone():
                    objProduction.closeMO()
            if objPick.sub_workorder_id:
                woBrws = objPick.env['mrp.workorder'].search([('id', '=', objPick.sub_workorder_id)])
                if woBrws and woBrws.state == 'external':
                    for line in objPick.move_lines:
                        if line.mrp_production_id == objProduction.id and line.state == 'done':
                            line.subContractingProduce(objProduction)
                        if woBrws.product_id.id == line.product_id.id:
                            woBrws.updateProducedQty(line.product_qty)
                        if line.purchase_order_line_subcontracting_id:
                            purchase_order_line_id = purchase_order_line.search([('id', '=', line.purchase_order_line_subcontracting_id)])
                            purchase_order_line_id._compute_qty_received()
                    woBrws.checkRecordProduction()

    def isIncoming(self, objPick):
        return objPick.picking_type_code == 'incoming'

    def isOutGoing(self, objPick):
        return objPick.picking_type_code == 'outgoing'

    def getStockQuant(self, stockQuantObj, lineId, prodBrws):
        quantsForProduct = stockQuantObj.search([
            ('location_id', '=', lineId),
            ('product_id', '=', prodBrws.id)])
        return quantsForProduct


class StockBackorderConfirmation(models.TransientModel):
    _name = 'stock.backorder.confirmation'
    _inherit = ['stock.backorder.confirmation']
    
    @api.multi
    def process(self):
        res = super(StockBackorderConfirmation, self).process()
        for objPick in self.pick_id:
            self.env['stock.picking'].commonSubcontracting(objPick)
        return res

    
class StockImmediateTransfer(models.TransientModel):
    _name = 'stock.immediate.transfer'
    _inherit = ['stock.immediate.transfer']

    @api.multi
    def process(self):
        res = super(StockImmediateTransfer, self).process()
        for objPick in self.pick_id:
            self.env['stock.picking'].commonSubcontracting(objPick)
        return res


class StockPackOperation(models.Model):
    _inherit = ['stock.pack.operation']

    @api.model
    def create(self, vals):
        res = super(StockPackOperation, self).create(vals)
        toWrite = {}
        if 'location_id' in vals:
            toWrite['location_id'] = vals['location_id']
        if 'location_dest_id' in vals:
            toWrite['location_dest_id'] = vals['location_dest_id']
        if toWrite:
            res.write(toWrite)
        return res

    @api.multi
    def write(self, vals):
        res = super(StockPackOperation, self).write(vals)
        return res