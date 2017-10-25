from openerp.osv import osv, fields


class StockTransferMaker(osv.osv_memory):
    _name = 'stock.transfer.maker'
    _columns = {
	'sale': fields.many2one('sale.order', 'Sale'),
	'transfer_lines': fields.one2many('stock.transfer.maker.line', 'sale', 'Transfer Lines'),
    }


    def make_transfer(self, cr, uid, ids, context=None):
	transfer = self.browse(cr, uid, ids[0])
	picking_obj = self.pool.get('stock.picking')
	move_obj = self.pool.get('stock.move')
	master = {}
	for move in transfer.transfer_lines:
	    if not master.get(move.location.id):
		master[move.location.id] = [move]
	    else:
		master[move.location.id].append(move)


	#TODO: DO not hardcode picking type
	transfer_id = 3
	for location, moves in master.items():
	    if not location:
		continue

	    transfer_vals = self.prepare_transfer_vals(cr, uid, transfer_id, \
		moves[0], moves[0].sale.sale
	    )

	    trans_id = picking_obj.create(cr, uid, transfer_vals)
	    trans = picking_obj.browse(cr, uid, trans_id)
	    for move in moves:
		line_vals = self.prepare_transfer_line_vals(cr, uid, move, trans)
		line = move_obj.create(cr, uid, line_vals)

	    picking_obj.action_confirm(cr, uid, [trans.id])
#	    picking_obj.action_assign(cr, uid, [trans.id])

	return True


    def prepare_transfer_vals(self, cr, uid, transfer_id, location, sale):
	vals = {
	    'origin': sale.name,
	    'picking_type_id': transfer_id,
	    'state': 'draft',
	    'note': 'Transfer of Goods for SO: %s From Location: %s' % (sale.name, location.location.name),
	    'invoice_state': 'none',
	    'company_id': sale.company_id.id,
	}

	return vals


    def prepare_transfer_line_vals(self, cr, uid, move, trans, context=None):
	move_obj = self.pool.get('stock.move')
	#Unassign previous pending moves
	ancestors = move_obj.find_move_ancestors(cr, uid, move.move, context=context)
	if ancestors:
	    move_obj.write(cr, uid, ancestors, {'move_dest_id': False}, context=context)

#	move.move.state = 'waiting'

	vals = {
		'name': move.move.name,
		'product_id': move.product.id,
#		'product_qty': move.qty,
		'product_uom': move.move.product_uom.id,
		'product_uom_qty': move.qty,
		'product_uos': move.move.product_uos.id,
		'location_id': move.location.id,
		'picking_id': trans.id,
		'company_id': move.move.company_id.id,
		'procure_method': 'make_to_stock',
		'move_dest_id': move.move.id,
		'priority': move.move.priority,
		'invoice_state': 'none',
		'weight_uom_id': move.move.weight_uom_id.id,
		'location_dest_id': move.move.location_id.id,
	}
	return vals


    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
	order_ids = context.get('active_ids', [])
	sale_obj = self.pool.get('sale.order')
	#There should only be one sale
	sale = sale_obj.browse(cr, uid, order_ids[0])

	res = {'sale': sale.id}
	transfer_lines = []
	for picking in sale.picking_ids:
	    for move in picking.move_lines:
		if move.state in ['waiting', 'confirmed']:
		    transfer_lines.append(self.prepare_transfer_line(cr, uid, sale, move))

	res.update({'transfer_lines': transfer_lines})
	return res


    def prepare_transfer_line(self, cr, uid, sale, move, context=None):
	vals = {
		'sale': sale.id,
		'product': move.product_id.id,
		'picking': move.picking_id.id,
		'qty': move.product_qty,
		'move': move.id,
	}

	return vals


class StocKTransferMakerLine(osv.osv_memory):
    _name = 'stock.transfer.maker.line'
    _columns = {
	'sale': fields.many2one('stock.transfer.maker', 'Sale'),
	'location': fields.many2one('stock.location', domain=[('usage', 'in', ['inventory', 'internal'])], string="Transfer From"),
	'product': fields.many2one('product.product', 'Product to Transfer'),
	'qty': fields.float('Quantity'),
	'picking': fields.many2one('stock.picking'),
	'move': fields.many2one('stock.move'),
    }
