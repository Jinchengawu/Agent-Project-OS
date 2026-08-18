import { mkdirSync, writeFileSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { randomUUID } from 'node:crypto'

export const name = 'agent-project-os-adapter'

function normalized(type) {
  return {
    'turn/start': 'agent.started',
    'turn/end': 'agent.ended',
    'tool/call': 'tool.started',
    'tool/result': 'tool.ended',
    'session/end-seed': 'session.ended',
  }[type]
}

function writeEvent(config, sessionId, normalizedEvent, sourceEvent, sequence) {
  const projectRoot = resolve(config?.projectRoot || process.cwd())
  const events = join(projectRoot, '.agent-project', 'events')
  mkdirSync(events, { recursive: true })
  const id = `adapter-event-${randomUUID().replaceAll('-', '')}`
  const event = {
    $schema: 'https://agent-project-os.org/schemas/runtime-adapter-event-v1.schema.json',
    protocol_version: '1.0',
    adapter_event_id: id,
    adapter: 'deepseek-harness',
    normalized_event: normalizedEvent,
    session_id: String(sessionId || 'unknown'),
    runtime_identity: {
      runtime: 'deepseek-harness',
      client_version: config?.clientVersion || 'preview-unknown',
    },
    payload: { source_event: String(sourceEvent), ...(sequence === undefined ? {} : { sequence }) },
    occurred_at: new Date().toISOString(),
  }
  writeFileSync(join(events, `${id}.json`), `${JSON.stringify(event, null, 2)}
`, { encoding: 'utf8', flag: 'wx' })
}

export function apply(ctx, config) {
  ctx.on('session/created', session => {
    writeEvent(config, session?.id, 'session.started', 'session/created')
  }, { global: true })
  ctx.on('session/event', (session, event) => {
    const mapped = normalized(event?.type)
    if (mapped) writeEvent(config, session?.id, mapped, event?.type, event?.seq)
  }, { global: true })
}
