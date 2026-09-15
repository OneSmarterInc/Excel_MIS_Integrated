// Sheet behaviour that has nothing to do with drawing: resolving formulas, copying them
// down, sorting rows and applying a number format. Kept apart from the component so it
// can be tested on its own.
import { evaluateFormula, toNumber } from './formula';

const PASSES = 4;

/** Work out what every cell displays, running a few passes so a helper column can feed a total. */
export function resolveGrid(rows) {
  let resolved = rows.map((row) => row.map((cell) => String(cell ?? '')));
  for (let pass = 0; pass < PASSES; pass += 1) {
    let changed = false;
    const next = resolved.map((row) => [...row]);
    rows.forEach((row, rowIndex) => {
      row.forEach((raw, colIndex) => {
        if (!String(raw ?? '').startsWith('=')) return;
        const outcome = evaluateFormula(raw, resolved);
        const shown = outcome.error
          ? outcome.error
          : typeof outcome.value === 'number'
          ? String(Math.round(outcome.value * 1e6) / 1e6)
          : String(outcome.value);
        if (next[rowIndex][colIndex] !== shown) {
          next[rowIndex][colIndex] = shown;
          changed = true;
        }
      });
    });
    resolved = next;
    if (!changed) break;
  }
  return resolved;
}

/** Copying a formula down shifts every row reference that is not locked with a dollar sign. */
export function shiftFormula(formula, rowDelta) {
  return formula.replace(
    /(\$?)([A-Za-z]{1,2})(\$?)(\d{1,5})/g,
    (whole, colLock, col, rowLock, row) =>
      rowLock === '$' ? whole : `${colLock}${col}${rowLock}${parseInt(row, 10) + rowDelta}`
  );
}

/** A number format changes how a value looks, never the value stored underneath. */
export function applyFormat(value, format) {
  if (!format || format.type === 'general') return value;
  const number = toNumber(value);
  if (number === null) return value;
  const decimals = format.decimals;
  switch (format.type) {
    case 'currency':
      return `$${number.toLocaleString(undefined, {
        minimumFractionDigits: decimals ?? 2,
        maximumFractionDigits: decimals ?? 2,
      })}`;
    case 'percent':
      return `${(number * 100).toFixed(decimals ?? 1)}%`;
    case 'comma':
      return number.toLocaleString(undefined, {
        minimumFractionDigits: decimals ?? 0,
        maximumFractionDigits: decimals ?? 0,
      });
    default:
      return value;
  }
}

/** Sort the body rows by one column, keeping the heading row where it is and blanks last. */
export function sortRows(rows, col, direction) {
  const header = rows[0];
  const body = rows.slice(1).map((row) => [...row]);
  body.sort((a, b) => {
    const leftBlank = String(a[col] ?? '') === '';
    const rightBlank = String(b[col] ?? '') === '';
    if (leftBlank && rightBlank) return 0;
    if (leftBlank) return 1;
    if (rightBlank) return -1;
    const left = toNumber(a[col]);
    const right = toNumber(b[col]);
    if (left !== null && right !== null) return direction === 'asc' ? left - right : right - left;
    const textLeft = String(a[col]).toLowerCase();
    const textRight = String(b[col]).toLowerCase();
    if (textLeft === textRight) return 0;
    const order = textLeft < textRight ? -1 : 1;
    return direction === 'asc' ? order : -order;
  });
  return [header, ...body];
}

/** The formula the Formulas tab drops into the formula bar for the current selection. */
export function functionFor(name, selection, columnLetterOf, lastRow) {
  if (name === 'IF') return '=IF(B2<C2,1,0)';
  if (!selection) return `=${name}()`;
  const column = columnLetterOf(selection.left);
  const range =
    selection.bottom > selection.top
      ? `${column}${selection.top + 1}:${column}${selection.bottom + 1}`
      : `${column}2:${column}${Math.max(2, lastRow)}`;
  return `=${name}(${range})`;
}
