export function normalizeOrder(order) {
  if (!order.order_id || !Number.isInteger(order.total_minor)) throw new TypeError('invalid orders@2 payload')
  return { id: order.order_id, totalMinor: order.total_minor }
}
