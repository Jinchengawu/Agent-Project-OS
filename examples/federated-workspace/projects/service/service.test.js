import assert from 'node:assert/strict'
import test from 'node:test'
import { normalizeOrder } from './service.js'

test('consumes orders@2', () => {
  assert.deepEqual(normalizeOrder({ order_id: 'o-1', total_minor: 1250 }), { id: 'o-1', totalMinor: 1250 })
})
