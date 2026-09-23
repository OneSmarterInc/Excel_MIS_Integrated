import React, { useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import {
  columnLetter,
  formatNumber,
  parseAddress,
  rangeCells,
  summarise,
  toNumber,
} from '../lib/formula';
import { applyFormat, functionFor, resolveGrid, shiftFormula, sortRows } from '../lib/sheet';
import { colors, mono } from '../theme';

const ROW_HEAD_WIDTH = 32;
const PASSES = 4;
const ZOOMS = [84, 104, 132];

// The window chrome borrows Excel's own colours so the panel reads as a spreadsheet
// window rather than as a table sitting inside a quiz.
const XL = {
  green: '#107C41',
  greenDark: '#0E6B38',
  chrome: '#F3F2F1',
  chromeLine: '#E1DFDD',
  headerFill: '#F5F5F5',
  headerText: '#616161',
  gridline: '#D0D7DE',
  selection: '#E8F2EC',
};

const TABS = ['Home', 'Formulas', 'Data', 'View'];


export default function InteractiveWorkbook({
  book,
  onUseValue,
  onAnswerCellChange,
  readOnly = false,
}) {
  // Real Excel always has empty columns and rows to work in, so the sheet is padded
  // out past the data. That spare space is where helper columns and scratch formulas go.
  const original = useMemo(() => {
    const source = (book?.rows || []).map((row) => row.map((cell) => String(cell ?? '')));
    const width = Math.max(3, ...source.map((row) => row.length)) + 2;
    const padded = source.map((row) => {
      const copy = [...row];
      while (copy.length < width) copy.push('');
      return copy;
    });
    for (let extra = 0; extra < 2; extra += 1) padded.push(new Array(width).fill(''));
    return padded;
  }, [book]);

  const [rows, setRows] = useState(original);
  const [anchor, setAnchor] = useState(null);
  const [focus, setFocus] = useState(null);
  const [extend, setExtend] = useState(false);
  const [entry, setEntry] = useState('');
  const [message, setMessage] = useState('');

  const [tab, setTab] = useState('Home');
  const [formats, setFormats] = useState({});
  const [bold, setBold] = useState({});
  const [italic, setItalic] = useState({});
  const [showFormulas, setShowFormulas] = useState(false);
  const [freeze, setFreeze] = useState(true);
  const [gridlines, setGridlines] = useState(true);
  const [formulaBar, setFormulaBar] = useState(true);
  const [zoom, setZoom] = useState(1);

  const cellWidth = ZOOMS[zoom];
  const resolved = useMemo(() => resolveGrid(rows), [rows]);
  const columns = (rows[0] || []).map((_, index) => columnLetter(index));
  const sheetName = book?.sheet || 'Sheet1';
  const fileName = (book?.file || 'Book1').replace(/\.xlsx?$/i, '');

  // The answer cell is an ordinary cell that the question is watching. Whatever it
  // resolves to, a typed number or the result of a formula, travels back up to the
  // question the moment it changes.
  const answerPoint = useMemo(
    () => (book?.answer_cell ? parseAddress(book.answer_cell) : null),
    [book]
  );
  const answerValue = answerPoint ? resolved[answerPoint.row]?.[answerPoint.col] ?? '' : '';

  useEffect(() => {
    if (!answerPoint || readOnly) return;
    const text = String(answerValue ?? '').trim();
    onAnswerCellChange?.(text.startsWith('#') ? '' : text);
  }, [answerValue, answerPoint, readOnly, onAnswerCellChange]);

  const selection = useMemo(() => {
    if (!anchor) return null;
    const end = focus || anchor;
    return {
      top: Math.min(anchor.row, end.row),
      bottom: Math.max(anchor.row, end.row),
      left: Math.min(anchor.col, end.col),
      right: Math.max(anchor.col, end.col),
    };
  }, [anchor, focus]);

  const reference = useMemo(() => {
    if (!selection) return '';
    const from = `${columnLetter(selection.left)}${selection.top + 1}`;
    const to = `${columnLetter(selection.right)}${selection.bottom + 1}`;
    return from === to ? from : `${from}:${to}`;
  }, [selection]);

  const stats = useMemo(
    () => (reference ? summarise(rangeCells(resolved, reference)) : null),
    [reference, resolved]
  );

  const eachSelectedCell = (change) => {
    if (!selection) return;
    const next = {};
    for (let row = selection.top; row <= selection.bottom; row += 1) {
      for (let col = selection.left; col <= selection.right; col += 1) {
        next[`${row},${col}`] = true;
      }
    }
    change(Object.keys(next));
  };

  const tapCell = (row, col) => {
    if (extend && anchor) {
      setFocus({ row, col });
      return;
    }
    setAnchor({ row, col });
    setFocus({ row, col });
    setEntry(rows[row]?.[col] ?? '');
    setMessage('');
  };

  const tapColumn = (col) => {
    setAnchor({ row: 1, col });
    setFocus({ row: rows.length - 1, col });
    setExtend(false);
  };

  const commit = () => {
    if (!anchor || readOnly) return;
    const next = rows.map((row) => [...row]);
    next[anchor.row][anchor.col] = entry;
    setRows(next);
    setMessage(`${columnLetter(anchor.col)}${anchor.row + 1} updated.`);
  };

  // ------------------------------------------------------------------ Home tab

  const setFormat = (type) => {
    eachSelectedCell((keys) => {
      setFormats((prev) => {
        const next = { ...prev };
        keys.forEach((key) => {
          next[key] = { type, decimals: next[key]?.decimals };
        });
        return next;
      });
    });
    setMessage(`${type === 'comma' ? 'Comma' : type[0].toUpperCase() + type.slice(1)} format applied to ${reference}.`);
  };

  const stepDecimals = (step) => {
    eachSelectedCell((keys) => {
      setFormats((prev) => {
        const next = { ...prev };
        keys.forEach((key) => {
          const current = next[key] || { type: 'comma' };
          const decimals = Math.max(0, Math.min(6, (current.decimals ?? 2) + step));
          next[key] = { ...current, decimals };
        });
        return next;
      });
    });
  };

  const toggleStyle = (setter) => {
    eachSelectedCell((keys) => {
      setter((prev) => {
        const next = { ...prev };
        const turningOn = !keys.every((key) => next[key]);
        keys.forEach((key) => {
          if (turningOn) next[key] = true;
          else delete next[key];
        });
        return next;
      });
    });
  };

  const clearCells = () => {
    if (!selection || readOnly) return;
    const next = rows.map((row) => [...row]);
    for (let row = selection.top; row <= selection.bottom; row += 1) {
      for (let col = selection.left; col <= selection.right; col += 1) next[row][col] = '';
    }
    setRows(next);
    setMessage(`${reference} cleared.`);
  };

  const autoSum = () => {
    if (!selection || readOnly) return;
    const col = selection.left;
    const target = selection.bottom > selection.top ? selection.bottom : rows.length - 2;
    const lastRow = Math.max(1, target - 1);
    const formula = `=SUM(${columnLetter(col)}2:${columnLetter(col)}${lastRow + 1})`;
    const next = rows.map((row) => [...row]);
    next[target][col] = formula;
    setRows(next);
    setAnchor({ row: target, col });
    setFocus({ row: target, col });
    setEntry(formula);
    setMessage(`AutoSum wrote ${formula} into ${columnLetter(col)}${target + 1}.`);
  };

  const fillDown = () => {
    if (!selection || selection.top === selection.bottom || readOnly) return;
    const source = rows[selection.top][selection.left];
    if (!source) return;
    const next = rows.map((row) => [...row]);
    for (let row = selection.top + 1; row <= selection.bottom; row += 1) {
      next[row][selection.left] = String(source).startsWith('=')
        ? shiftFormula(source, row - selection.top)
        : source;
    }
    setRows(next);
    setMessage(`Filled ${reference} down from the top cell.`);
  };

  // -------------------------------------------------------------- Formulas tab

  // Clicking a function in Excel writes it into the selected cell. With a range selected
  // it lands in the cell just below the range, which is where a total belongs.
  const insertFunction = (name) => {
    if (readOnly) return;
    if (!selection) {
      setMessage('Select a cell first, then choose the function.');
      return;
    }
    const formula = functionFor(name, selection, columnLetter, rows.length - 2);
    const target =
      selection.bottom > selection.top
        ? { row: Math.min(selection.bottom + 1, rows.length - 1), col: selection.left }
        : { row: selection.top, col: selection.left };
    const next = rows.map((row) => [...row]);
    next[target.row][target.col] = formula;
    setRows(next);
    setAnchor(target);
    setFocus(target);
    setEntry(formula);
    setMessage(`${formula} written into ${columnLetter(target.col)}${target.row + 1}.`);
  };

  // ------------------------------------------------------------------ Data tab

  const sortBy = (direction) => {
    if (!selection || readOnly) return;
    const col = selection.left;
    setRows(sortRows(rows, col, direction));
    setMessage(
      `Sorted by column ${columnLetter(col)} ${direction === 'asc' ? 'A to Z' : 'Z to A'}.`
    );
  };

  const reset = () => {
    setRows(original);
    setAnchor(null);
    setFocus(null);
    setEntry('');
    setFormats({});
    setBold({});
    setItalic({});
    setMessage('The sheet is back as it arrived.');
  };

  const push = (value) => {
    if (value === null || value === undefined || value === '') return;
    onUseValue?.(typeof value === 'number' ? String(Math.round(value * 100) / 100) : String(value));
    setMessage('Value sent up to your answer box.');
  };

  const activeValue = anchor ? resolved[anchor.row]?.[anchor.col] ?? '' : '';

  const renderRow = (row, rowIndex) => {
    const rowActive = selection && rowIndex >= selection.top && rowIndex <= selection.bottom;
    return (
      <View key={`r${rowIndex}`} style={styles.row}>
        <View style={[styles.rowHead, rowActive && styles.headActive]}>
          <Text style={[styles.headText, rowActive && styles.headTextActive]}>{rowIndex + 1}</Text>
        </View>
        {columns.map((_, colIndex) => {
          const raw = rows[rowIndex]?.[colIndex] ?? '';
          const key = `${rowIndex},${colIndex}`;
          const hasFormula = String(raw).startsWith('=');
          const shown = showFormulas
            ? raw
            : applyFormat(row[colIndex] ?? '', formats[key]);
          const inSelection =
            selection &&
            rowIndex >= selection.top && rowIndex <= selection.bottom &&
            colIndex >= selection.left && colIndex <= selection.right;
          const isAnchor = anchor && anchor.row === rowIndex && anchor.col === colIndex;
          const isAnswer =
            answerPoint && answerPoint.row === rowIndex && answerPoint.col === colIndex;
          const numeric = toNumber(row[colIndex]) !== null;
          return (
            <Pressable
              key={`c${colIndex}`}
              onPress={() => tapCell(rowIndex, colIndex)}
              style={[
                styles.cell,
                { width: cellWidth },
                !gridlines && styles.cellNoLines,
                inSelection && styles.cellSelected,
                isAnswer && styles.cellAnswer,
                isAnchor && styles.cellAnchor,
              ]}
            >
              <Text
                numberOfLines={1}
                style={[
                  styles.cellText,
                  rowIndex === 0 && styles.cellHeaderText,
                  hasFormula && !showFormulas && { color: XL.green },
                  bold[key] && { fontWeight: '700' },
                  italic[key] && { fontStyle: 'italic' },
                  numeric && rowIndex > 0 && !showFormulas && { textAlign: 'right' },
                ]}
              >
                {shown}
              </Text>
            </Pressable>
          );
        })}
      </View>
    );
  };

  return (
    <View style={styles.window}>
      <View style={styles.titleBar}>
        <View style={styles.appMark}>
          <Text style={styles.appMarkText}>X</Text>
        </View>
        <Text style={styles.titleText} numberOfLines={1}>{fileName} — Excel</Text>
      </View>

      <View style={styles.tabStrip}>
        {TABS.map((name) => {
          const active = name === tab;
          return (
            <Pressable key={name} onPress={() => setTab(name)} style={[styles.tab, active && styles.tabActive]}>
              <Text style={[styles.tabText, active && styles.tabTextActive]}>{name}</Text>
            </Pressable>
          );
        })}
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.ribbonScroll}>
        <View style={styles.ribbon}>
          {tab === 'Home' ? (
            <>
              <Group label="Font">
                <RibbonButton glyph="B" label="Bold" onPress={() => toggleStyle(setBold)} disabled={!selection || readOnly} />
                <RibbonButton glyph="I" label="Italic" onPress={() => toggleStyle(setItalic)} disabled={!selection || readOnly} />
              </Group>
              <Group label="Number">
                <RibbonButton glyph="123" label="General" onPress={() => setFormat('general')} disabled={!selection} />
                <RibbonButton glyph="$" label="Currency" onPress={() => setFormat('currency')} disabled={!selection} />
                <RibbonButton glyph="%" label="Percent" onPress={() => setFormat('percent')} disabled={!selection} />
                <RibbonButton glyph="," label="Comma" onPress={() => setFormat('comma')} disabled={!selection} />
                <RibbonButton glyph=".0+" label="Add dp" onPress={() => stepDecimals(1)} disabled={!selection} />
                <RibbonButton glyph=".0-" label="Less dp" onPress={() => stepDecimals(-1)} disabled={!selection} />
              </Group>
              <Group label="Editing">
                <RibbonButton glyph="Σ" label="AutoSum" onPress={autoSum} disabled={!selection || readOnly} />
                <RibbonButton glyph="↓" label="Fill down" onPress={fillDown} disabled={!selection || readOnly} />
                <RibbonButton glyph="⌫" label="Clear" onPress={clearCells} disabled={!selection || readOnly} />
              </Group>
            </>
          ) : null}

          {tab === 'Formulas' ? (
            <>
              <Group label="Function library">
                <RibbonButton glyph="Σ" label="SUM" onPress={() => insertFunction('SUM')} disabled={readOnly} />
                <RibbonButton glyph="x̄" label="AVERAGE" onPress={() => insertFunction('AVERAGE')} disabled={readOnly} />
                <RibbonButton glyph="#" label="COUNT" onPress={() => insertFunction('COUNT')} disabled={readOnly} />
                <RibbonButton glyph="↓" label="MIN" onPress={() => insertFunction('MIN')} disabled={readOnly} />
                <RibbonButton glyph="↑" label="MAX" onPress={() => insertFunction('MAX')} disabled={readOnly} />
              </Group>
              <Group label="Logical and lookup">
                <RibbonButton glyph="?" label="IF" onPress={() => insertFunction('IF')} disabled={readOnly} />
                <RibbonButton glyph="Σ?" label="SUMIF" onPress={() => insertFunction('SUMIF')} disabled={readOnly} />
                <RibbonButton glyph="#?" label="COUNTIF" onPress={() => insertFunction('COUNTIF')} disabled={readOnly} />
              </Group>
              <Group label="Auditing">
                <RibbonButton
                  glyph="fx"
                  label="Show formulas"
                  active={showFormulas}
                  onPress={() => setShowFormulas((on) => !on)}
                />
                <RibbonButton glyph="↻" label="Recalculate" onPress={() => setRows((current) => current.map((row) => [...row]))} />
              </Group>
            </>
          ) : null}

          {tab === 'Data' ? (
            <>
              <Group label="Sort and Filter">
                <RibbonButton glyph="A↓" label="A to Z" onPress={() => sortBy('asc')} disabled={!selection || readOnly} />
                <RibbonButton glyph="Z↓" label="Z to A" onPress={() => sortBy('desc')} disabled={!selection || readOnly} />
              </Group>
              <Group label="Select">
                <RibbonButton
                  glyph="⬚"
                  label={extend ? 'Extending' : 'Extend'}
                  active={extend}
                  onPress={() => setExtend((on) => !on)}
                />
                <RibbonButton
                  glyph="▤"
                  label="Whole column"
                  onPress={() => selection && tapColumn(selection.left)}
                  disabled={!selection}
                />
              </Group>
              <Group label="Data tools">
                <RibbonButton glyph="↺" label="Reset" onPress={reset} disabled={readOnly} />
              </Group>
            </>
          ) : null}

          {tab === 'View' ? (
            <>
              <Group label="Window">
                <RibbonButton
                  glyph="⊞"
                  label={freeze ? 'Unfreeze' : 'Freeze row 1'}
                  active={freeze}
                  onPress={() => setFreeze((on) => !on)}
                />
                <RibbonButton
                  glyph="fx"
                  label="Formula bar"
                  active={formulaBar}
                  onPress={() => setFormulaBar((on) => !on)}
                />
              </Group>
              <Group label="Show">
                <RibbonButton
                  glyph="▦"
                  label="Gridlines"
                  active={gridlines}
                  onPress={() => setGridlines((on) => !on)}
                />
              </Group>
              <Group label="Zoom">
                <RibbonButton glyph="−" label="Narrower" onPress={() => setZoom((z) => Math.max(0, z - 1))} disabled={zoom === 0} />
                <RibbonButton glyph="+" label="Wider" onPress={() => setZoom((z) => Math.min(ZOOMS.length - 1, z + 1))} disabled={zoom === ZOOMS.length - 1} />
              </Group>
            </>
          ) : null}
        </View>
      </ScrollView>

      {formulaBar ? (
        <View style={styles.formulaBar}>
          <View style={styles.nameBox}>
            <Text style={styles.nameBoxText} numberOfLines={1}>{reference || 'A1'}</Text>
          </View>
          <Text style={styles.fx}>fx</Text>
          <TextInput
            value={entry}
            onChangeText={setEntry}
            onSubmitEditing={commit}
            editable={!!anchor && !readOnly}
            placeholder={anchor ? 'Type a value or =B2*C2' : 'Select a cell'}
            placeholderTextColor="#9AA5B1"
            style={styles.formulaInput}
            autoCapitalize="characters"
            autoCorrect={false}
          />
          <Pressable
            onPress={commit}
            disabled={!anchor || readOnly}
            style={[styles.enterButton, (!anchor || readOnly) && { opacity: 0.4 }]}
          >
            <Text style={styles.enterButtonText}>Enter</Text>
          </Pressable>
        </View>
      ) : null}

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.gridWrap}>
        <View>
          <View style={styles.row}>
            <View style={[styles.rowHead, styles.corner]} />
            {columns.map((letter, colIndex) => {
              const active = selection && colIndex >= selection.left && colIndex <= selection.right;
              return (
                <Pressable
                  key={letter}
                  onPress={() => tapColumn(colIndex)}
                  style={[styles.colHead, { width: cellWidth }, active && styles.headActive]}
                >
                  <Text style={[styles.headText, active && styles.headTextActive]}>{letter}</Text>
                </Pressable>
              );
            })}
          </View>

          {freeze ? renderRow(resolved[0] || [], 0) : null}

          <ScrollView style={{ maxHeight: 280 }} showsVerticalScrollIndicator={false}>
            {resolved.map((row, rowIndex) =>
              freeze && rowIndex === 0 ? null : renderRow(row, rowIndex)
            )}
          </ScrollView>
        </View>
      </ScrollView>

      <View style={styles.tabBar}>
        <View style={styles.sheetTab}>
          <Text style={styles.sheetTabText}>{sheetName}</Text>
        </View>
        {activeValue !== '' ? (
          <Text style={styles.activeValue} numberOfLines={1}>
            {reference}: {activeValue}
          </Text>
        ) : null}
      </View>

      <View style={styles.statusBar}>
        {stats && stats.count ? (
          <>
            <StatusItem label="Average" value={formatNumber(stats.average)} onPress={() => push(stats.average)} />
            <StatusItem label="Count" value={String(stats.count)} onPress={() => push(stats.count)} />
            <StatusItem label="Min" value={formatNumber(stats.min)} onPress={() => push(stats.min)} />
            <StatusItem label="Max" value={formatNumber(stats.max)} onPress={() => push(stats.max)} />
            <StatusItem label="Sum" value={formatNumber(stats.sum)} onPress={() => push(stats.sum)} />
          </>
        ) : (
          <Text style={styles.statusHint}>
            Tap a cell, or a column letter for the whole column. Turn on Extend under Data and tap
            a second cell for a range.
          </Text>
        )}
      </View>

      {message ? <Text style={styles.message}>{message}</Text> : null}
      {book?.note ? <Text style={styles.note}>{book.note}</Text> : null}
    </View>
  );
}

function Group({ label, children }) {
  return (
    <View style={styles.group}>
      <View style={styles.groupRow}>{children}</View>
      <Text style={styles.groupLabel}>{label}</Text>
    </View>
  );
}

function RibbonButton({ glyph, label, onPress, disabled, active }) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[styles.ribbonButton, active && styles.ribbonButtonActive, disabled && { opacity: 0.35 }]}
    >
      <Text style={[styles.ribbonGlyph, active && { color: colors.paper }]}>{glyph}</Text>
      <Text style={[styles.ribbonLabel, active && { color: colors.paper }]}>{label}</Text>
    </Pressable>
  );
}

function StatusItem({ label, value, onPress }) {
  return (
    <Pressable onPress={onPress} style={styles.statusItem}>
      <Text style={styles.statusText}>
        {label}: <Text style={styles.statusValue}>{value}</Text>
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  window: {
    borderWidth: 1,
    borderColor: XL.chromeLine,
    backgroundColor: colors.paper,
    overflow: 'hidden',
  },
  titleBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: XL.chrome,
    borderBottomWidth: 1,
    borderBottomColor: XL.chromeLine,
    paddingHorizontal: 8,
    paddingVertical: 6,
  },
  appMark: {
    width: 20,
    height: 20,
    backgroundColor: XL.green,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
    borderRadius: 3,
  },
  appMarkText: { color: colors.paper, fontSize: 12, fontWeight: '700' },
  titleText: { fontSize: 12.5, color: '#333333', fontWeight: '600', flex: 1 },
  tabStrip: {
    flexDirection: 'row',
    backgroundColor: colors.paper,
    borderBottomWidth: 1,
    borderBottomColor: XL.chromeLine,
    paddingHorizontal: 6,
  },
  tab: { paddingHorizontal: 12, paddingVertical: 8, borderBottomWidth: 2, borderBottomColor: 'transparent' },
  tabActive: { borderBottomColor: XL.green },
  tabText: { fontSize: 12.5, color: '#4B5563' },
  tabTextActive: { color: XL.green, fontWeight: '700' },
  ribbonScroll: { backgroundColor: XL.chrome, borderBottomWidth: 1, borderBottomColor: XL.chromeLine },
  ribbon: { flexDirection: 'row', paddingHorizontal: 6, paddingTop: 6, paddingBottom: 2 },
  group: {
    borderRightWidth: 1,
    borderRightColor: XL.chromeLine,
    paddingHorizontal: 8,
    paddingBottom: 3,
  },
  groupRow: { flexDirection: 'row' },
  groupLabel: { fontSize: 9.5, color: XL.headerText, textAlign: 'center', marginTop: 2 },
  ribbonButton: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 7,
    paddingVertical: 4,
    marginHorizontal: 2,
    borderRadius: 3,
    minWidth: 46,
  },
  ribbonButtonActive: { backgroundColor: XL.green },
  ribbonGlyph: { fontSize: 15, color: '#3A3A3A', marginBottom: 1 },
  ribbonLabel: { fontSize: 9.5, color: '#3A3A3A' },
  formulaBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.paper,
    borderBottomWidth: 1,
    borderBottomColor: XL.chromeLine,
    paddingHorizontal: 6,
    paddingVertical: 5,
  },
  nameBox: {
    width: 66,
    borderWidth: 1,
    borderColor: XL.gridline,
    paddingVertical: 5,
    alignItems: 'center',
    marginRight: 6,
  },
  nameBoxText: { fontFamily: mono, fontSize: 11.5, color: colors.ink },
  fx: { fontFamily: mono, fontSize: 12, color: XL.headerText, fontStyle: 'italic', marginRight: 6 },
  formulaInput: {
    flex: 1,
    fontFamily: mono,
    fontSize: 12.5,
    color: colors.ink,
    borderWidth: 1,
    borderColor: XL.gridline,
    paddingHorizontal: 8,
    paddingVertical: 6,
    marginRight: 6,
  },
  enterButton: {
    backgroundColor: XL.green,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 3,
  },
  enterButtonText: { color: colors.paper, fontSize: 11.5, fontWeight: '700' },
  gridWrap: { backgroundColor: colors.paper },
  row: { flexDirection: 'row' },
  rowHead: {
    width: ROW_HEAD_WIDTH,
    backgroundColor: XL.headerFill,
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: XL.gridline,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
  },
  corner: { borderBottomWidth: 1 },
  colHead: {
    backgroundColor: XL.headerFill,
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: XL.gridline,
    alignItems: 'center',
    paddingVertical: 6,
  },
  headActive: { backgroundColor: XL.selection },
  headText: { fontFamily: mono, fontSize: 11, color: XL.headerText },
  headTextActive: { color: XL.greenDark, fontWeight: '700' },
  cell: {
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: XL.gridline,
    paddingHorizontal: 6,
    paddingVertical: 8,
    justifyContent: 'center',
  },
  cellNoLines: { borderColor: 'transparent' },
  cellSelected: { backgroundColor: XL.selection },
  cellAnswer: { backgroundColor: '#FBF0E0', borderWidth: 1, borderColor: '#C2761F' },
  cellAnchor: { borderWidth: 2, borderColor: XL.green },
  cellText: { fontFamily: mono, fontSize: 12, color: colors.ink },
  cellHeaderText: { fontWeight: '700', color: '#3A3A3A' },
  tabBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: XL.chrome,
    borderTopWidth: 1,
    borderTopColor: XL.chromeLine,
    paddingHorizontal: 6,
    paddingVertical: 4,
  },
  sheetTab: {
    backgroundColor: colors.paper,
    borderTopWidth: 2,
    borderTopColor: XL.green,
    paddingHorizontal: 12,
    paddingVertical: 5,
  },
  sheetTabText: { fontSize: 11.5, color: XL.greenDark, fontWeight: '700' },
  activeValue: { fontFamily: mono, fontSize: 11, color: XL.headerText, marginLeft: 10, flex: 1 },
  statusBar: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    backgroundColor: XL.chrome,
    borderTopWidth: 1,
    borderTopColor: XL.chromeLine,
    paddingHorizontal: 8,
    paddingVertical: 5,
  },
  statusItem: { marginRight: 14, paddingVertical: 2 },
  statusText: { fontSize: 11.5, color: '#3A3A3A' },
  statusValue: { fontFamily: mono, fontWeight: '700', color: colors.ink },
  statusHint: { fontSize: 11, color: XL.headerText, flex: 1 },
  message: {
    fontSize: 11.5,
    color: XL.greenDark,
    backgroundColor: '#EEF7F1',
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  note: {
    fontSize: 11.5,
    color: XL.headerText,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderTopWidth: 1,
    borderTopColor: XL.chromeLine,
  },
});
