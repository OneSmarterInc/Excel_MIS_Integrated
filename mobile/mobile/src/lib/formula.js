// A small spreadsheet engine: enough of Excel's grammar for the business questions.
// It understands numbers, text, cell addresses, ranges, the arithmetic operators,
// comparisons, and the functions the course actually teaches.

const FUNCTIONS = [
  'SUM', 'AVERAGE', 'AVG', 'COUNT', 'COUNTA', 'COUNTBLANK', 'MIN', 'MAX', 'MEDIAN',
  'ROUND', 'ROUNDUP', 'ROUNDDOWN', 'ABS', 'INT', 'IF', 'SUMIF', 'COUNTIF', 'AVERAGEIF',
  'SUMPRODUCT', 'PRODUCT', 'LARGE', 'SMALL', 'SQRT', 'POWER',
];

export const SUPPORTED_FUNCTIONS = FUNCTIONS;

// "$1,240.00" and "18.5%" are numbers as far as the status bar is concerned.
export function toNumber(raw) {
  if (raw === null || raw === undefined) return null;
  if (typeof raw === 'number') return Number.isFinite(raw) ? raw : null;
  let text = String(raw).trim();
  if (!text) return null;
  let percent = false;
  if (text.endsWith('%')) {
    percent = true;
    text = text.slice(0, -1);
  }
  let negative = false;
  if (text.startsWith('(') && text.endsWith(')')) {
    negative = true;
    text = text.slice(1, -1);
  }
  text = text.replace(/[$,\s]/g, '');
  if (!/^-?\d*\.?\d+(e-?\d+)?$/i.test(text)) return null;
  let value = parseFloat(text);
  if (percent) value /= 100;
  if (negative) value = -value;
  return Number.isFinite(value) ? value : null;
}

export function columnIndex(letters) {
  let index = 0;
  for (const character of letters.toUpperCase()) {
    index = index * 26 + (character.charCodeAt(0) - 64);
  }
  return index - 1;
}

export function columnLetter(index) {
  let letters = '';
  let value = index + 1;
  while (value > 0) {
    const remainder = (value - 1) % 26;
    letters = String.fromCharCode(65 + remainder) + letters;
    value = Math.floor((value - remainder) / 26);
  }
  return letters;
}

export function parseAddress(address) {
  const match = /^\$?([A-Za-z]{1,2})\$?(\d{1,5})$/.exec(String(address).trim());
  if (!match) return null;
  return { col: columnIndex(match[1]), row: parseInt(match[2], 10) - 1 };
}

export function cellRaw(grid, address) {
  const point = parseAddress(address);
  if (!point) return '';
  const row = grid[point.row];
  if (!row) return '';
  return row[point.col] ?? '';
}

// A range comes back as a list of {row, col, raw} so functions can use either the
// values or the positions.
export function rangeCells(grid, reference) {
  const [start, end] = String(reference).split(':');
  const from = parseAddress(start);
  const to = parseAddress(end || start);
  if (!from || !to) return [];
  const cells = [];
  for (let row = Math.min(from.row, to.row); row <= Math.max(from.row, to.row); row += 1) {
    for (let col = Math.min(from.col, to.col); col <= Math.max(from.col, to.col); col += 1) {
      cells.push({ row, col, raw: grid[row]?.[col] ?? '' });
    }
  }
  return cells;
}

export function summarise(cells) {
  const numbers = cells.map((cell) => toNumber(cell.raw)).filter((value) => value !== null);
  const filled = cells.filter((cell) => String(cell.raw).trim() !== '').length;
  if (!numbers.length) {
    return { count: 0, filled, sum: null, average: null, min: null, max: null };
  }
  const sum = numbers.reduce((total, value) => total + value, 0);
  return {
    count: numbers.length,
    filled,
    sum,
    average: sum / numbers.length,
    min: Math.min(...numbers),
    max: Math.max(...numbers),
  };
}

// --------------------------------------------------------------------- tokeniser

function tokenise(input) {
  const tokens = [];
  let index = 0;
  while (index < input.length) {
    const character = input[index];
    if (/\s/.test(character)) {
      index += 1;
      continue;
    }
    if (character === '"') {
      let text = '';
      index += 1;
      while (index < input.length && input[index] !== '"') {
        text += input[index];
        index += 1;
      }
      index += 1;
      tokens.push({ type: 'text', value: text });
      continue;
    }
    const twoChar = input.slice(index, index + 2);
    if (['<=', '>=', '<>'].includes(twoChar)) {
      tokens.push({ type: 'op', value: twoChar });
      index += 2;
      continue;
    }
    if ('+-*/^(),&<>='.includes(character)) {
      tokens.push({ type: 'op', value: character });
      index += 1;
      continue;
    }
    const rest = input.slice(index);
    const range = /^\$?[A-Za-z]{1,2}\$?\d{1,5}\s*:\s*\$?[A-Za-z]{1,2}\$?\d{1,5}/.exec(rest);
    if (range) {
      tokens.push({ type: 'range', value: range[0].replace(/\s/g, '') });
      index += range[0].length;
      continue;
    }
    const name = /^[A-Za-z][A-Za-z0-9_.]*/.exec(rest);
    if (name) {
      const upper = name[0].toUpperCase();
      const address = parseAddress(name[0]);
      if (address && !FUNCTIONS.includes(upper)) {
        tokens.push({ type: 'cell', value: name[0] });
      } else {
        tokens.push({ type: 'name', value: upper });
      }
      index += name[0].length;
      continue;
    }
    const number = /^\d*\.?\d+(e-?\d+)?/i.exec(rest);
    if (number) {
      tokens.push({ type: 'number', value: parseFloat(number[0]) });
      index += number[0].length;
      continue;
    }
    throw new Error(`Cannot read "${character}"`);
  }
  return tokens;
}

// ----------------------------------------------------------------------- parser

function evaluateFunction(name, args, grid) {
  const flatten = (list) =>
    list.flatMap((arg) => (Array.isArray(arg) ? arg.map((cell) => cell.raw) : [arg]));
  const numbersOf = (list) =>
    flatten(list).map((value) => toNumber(value)).filter((value) => value !== null);

  const matches = (raw, condition) => {
    const text = String(raw).trim();
    const test = String(condition).trim();
    const operator = /^(<=|>=|<>|<|>|=)(.*)$/.exec(test);
    if (operator) {
      const target = toNumber(operator[2]);
      const value = toNumber(raw);
      if (target === null || value === null) {
        return operator[1] === '<>'
          ? text.toLowerCase() !== operator[2].trim().toLowerCase()
          : text.toLowerCase() === operator[2].trim().toLowerCase();
      }
      switch (operator[1]) {
        case '<': return value < target;
        case '>': return value > target;
        case '<=': return value <= target;
        case '>=': return value >= target;
        case '<>': return value !== target;
        default: return value === target;
      }
    }
    if (test.includes('*')) {
      const pattern = new RegExp(`^${test.replace(/\*/g, '.*')}$`, 'i');
      return pattern.test(text);
    }
    return text.toLowerCase() === test.toLowerCase();
  };

  const numbers = numbersOf(args);
  switch (name) {
    case 'SUM':
      return numbers.reduce((total, value) => total + value, 0);
    case 'PRODUCT':
      return numbers.reduce((total, value) => total * value, 1);
    case 'AVERAGE':
    case 'AVG':
      if (!numbers.length) throw new Error('#DIV/0!');
      return numbers.reduce((total, value) => total + value, 0) / numbers.length;
    case 'COUNT':
      return numbers.length;
    case 'COUNTA':
      return flatten(args).filter((value) => String(value).trim() !== '').length;
    case 'COUNTBLANK':
      return flatten(args).filter((value) => String(value).trim() === '').length;
    case 'MIN':
      return numbers.length ? Math.min(...numbers) : 0;
    case 'MAX':
      return numbers.length ? Math.max(...numbers) : 0;
    case 'MEDIAN': {
      const sorted = [...numbers].sort((a, b) => a - b);
      const middle = Math.floor(sorted.length / 2);
      if (!sorted.length) throw new Error('#NUM!');
      return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
    }
    case 'LARGE':
      return [...numbers].sort((a, b) => b - a)[Math.round(args[1]) - 1] ?? 0;
    case 'SMALL':
      return [...numbers].sort((a, b) => a - b)[Math.round(args[1]) - 1] ?? 0;
    case 'ROUND': {
      const places = Math.round(args[1] ?? 0);
      const factor = 10 ** places;
      return Math.round(numbers[0] * factor) / factor;
    }
    case 'ROUNDUP': {
      const factor = 10 ** Math.round(args[1] ?? 0);
      return Math.ceil(numbers[0] * factor) / factor;
    }
    case 'ROUNDDOWN': {
      const factor = 10 ** Math.round(args[1] ?? 0);
      return Math.floor(numbers[0] * factor) / factor;
    }
    case 'ABS':
      return Math.abs(numbers[0]);
    case 'INT':
      return Math.floor(numbers[0]);
    case 'SQRT':
      return Math.sqrt(numbers[0]);
    case 'POWER':
      return numbers[0] ** numbers[1];
    case 'IF':
      return args[0] ? args[1] : args[2] ?? false;
    case 'COUNTIF': {
      const cells = Array.isArray(args[0]) ? args[0] : [];
      return cells.filter((cell) => matches(cell.raw, args[1])).length;
    }
    case 'SUMIF':
    case 'AVERAGEIF': {
      const tested = Array.isArray(args[0]) ? args[0] : [];
      const summed = Array.isArray(args[2]) ? args[2] : tested;
      const picked = [];
      tested.forEach((cell, position) => {
        if (matches(cell.raw, args[1])) {
          const value = toNumber(summed[position]?.raw);
          if (value !== null) picked.push(value);
        }
      });
      const total = picked.reduce((sum, value) => sum + value, 0);
      if (name === 'SUMIF') return total;
      if (!picked.length) throw new Error('#DIV/0!');
      return total / picked.length;
    }
    case 'SUMPRODUCT': {
      const lists = args.filter(Array.isArray);
      if (!lists.length) return 0;
      return lists[0].reduce((total, _, position) => {
        const product = lists.reduce(
          (running, list) => running * (toNumber(list[position]?.raw) ?? 0), 1
        );
        return total + product;
      }, 0);
    }
    default:
      throw new Error('#NAME?');
  }
}

function parse(tokens, grid) {
  let position = 0;
  const peek = () => tokens[position];
  const take = () => tokens[position++];

  function primary() {
    const token = take();
    if (!token) throw new Error('The formula ends too early');
    if (token.type === 'number') return token.value;
    if (token.type === 'text') return token.value;
    if (token.type === 'cell') return toNumber(cellRaw(grid, token.value)) ?? cellRaw(grid, token.value);
    if (token.type === 'range') return rangeCells(grid, token.value);
    if (token.type === 'op' && token.value === '(') {
      const value = comparison();
      if (!peek() || peek().value !== ')') throw new Error('A bracket is not closed');
      take();
      return value;
    }
    if (token.type === 'op' && token.value === '-') return -primary();
    if (token.type === 'op' && token.value === '+') return primary();
    if (token.type === 'name') {
      if (!peek() || peek().value !== '(') throw new Error('#NAME?');
      take();
      const args = [];
      if (peek() && peek().value !== ')') {
        args.push(comparison());
        while (peek() && peek().value === ',') {
          take();
          args.push(comparison());
        }
      }
      if (!peek() || peek().value !== ')') throw new Error('A bracket is not closed');
      take();
      return evaluateFunction(token.value, args, grid);
    }
    throw new Error(`Unexpected ${token.value}`);
  }

  function power() {
    let left = primary();
    while (peek() && peek().value === '^') {
      take();
      left = Number(left) ** Number(primary());
    }
    return left;
  }

  function term() {
    let left = power();
    while (peek() && (peek().value === '*' || peek().value === '/')) {
      const operator = take().value;
      const right = power();
      if (operator === '/' && Number(right) === 0) throw new Error('#DIV/0!');
      left = operator === '*' ? Number(left) * Number(right) : Number(left) / Number(right);
    }
    return left;
  }

  function sum() {
    let left = term();
    while (peek() && ['+', '-', '&'].includes(peek().value)) {
      const operator = take().value;
      const right = term();
      if (operator === '&') left = `${left}${right}`;
      else left = operator === '+' ? Number(left) + Number(right) : Number(left) - Number(right);
    }
    return left;
  }

  function comparison() {
    let left = sum();
    while (peek() && ['<', '>', '<=', '>=', '=', '<>'].includes(peek().value)) {
      const operator = take().value;
      const right = sum();
      const a = typeof left === 'string' ? left.toLowerCase() : left;
      const b = typeof right === 'string' ? right.toLowerCase() : right;
      switch (operator) {
        case '<': left = a < b; break;
        case '>': left = a > b; break;
        case '<=': left = a <= b; break;
        case '>=': left = a >= b; break;
        case '<>': left = a !== b; break;
        default: left = a === b;
      }
    }
    return left;
  }

  const result = comparison();
  if (position < tokens.length) throw new Error('There is something extra at the end');
  return result;
}

/** Evaluate a formula against the grid. Returns { value } or { error }. */
export function evaluateFormula(input, grid) {
  const text = String(input || '').trim();
  if (!text) return { value: '' };
  const body = text.startsWith('=') ? text.slice(1) : text;
  try {
    const value = parse(tokenise(body), grid);
    if (Array.isArray(value)) {
      const stats = summarise(value);
      return { value: stats.sum ?? 0 };
    }
    if (typeof value === 'number' && !Number.isFinite(value)) return { error: '#NUM!' };
    return { value };
  } catch (error) {
    return { error: error.message?.startsWith('#') ? error.message : error.message || '#ERROR' };
  }
}

export function formatNumber(value, places = 2) {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value === 'boolean') return value ? 'TRUE' : 'FALSE';
  if (typeof value !== 'number') return String(value);
  const rounded = Math.round(value * 10 ** places) / 10 ** places;
  return rounded.toLocaleString(undefined, { maximumFractionDigits: places });
}
