// Minimal Server-Sent Events parser for fetch() streams.
// (The browser's EventSource only supports GET, but we POST the question.)
export function createSseParser(onEvent) {
  let buffer = '';

  function dispatch(block) {
    let event = 'message';
    const dataLines = [];
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
    }
    if (dataLines.length) onEvent(event, JSON.parse(dataLines.join('\n')));
  }

  return {
    push(chunk) {
      buffer = (buffer + chunk).replace(/\r\n/g, '\n');
      let end;
      while ((end = buffer.indexOf('\n\n')) !== -1) {
        dispatch(buffer.slice(0, end));
        buffer = buffer.slice(end + 2);
      }
    },
    end() {
      if (buffer.trim()) dispatch(buffer);
      buffer = '';
    },
  };
}