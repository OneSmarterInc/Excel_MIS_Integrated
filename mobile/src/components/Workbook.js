import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors, mono, spacing } from '../theme';

const CELL_WIDTH = 108;
const ROW_HEAD_WIDTH = 30;

// A highlight arrives as "B2:B6" or "C3". Both are turned into a set of addresses
// so the same code can shade a single cell or a whole range.
function highlightSet(highlights = []) {
  const cells = new Set();
  highlights.forEach((entry) => {
    const [start, end] = String(entry).split(':');
    const parse = (address) => {
      const match = /^([A-Z]+)(\d+)$/.exec(address.trim().toUpperCase());
      return match ? { col: match[1].charCodeAt(0) - 65, row: Number(match[2]) } : null;
    };
    const from = parse(start);
    const to = end ? parse(end) : from;
    if (!from || !to) return;
    for (let col = Math.min(from.col, to.col); col <= Math.max(from.col, to.col); col += 1) {
      for (let row = Math.min(from.row, to.row); row <= Math.max(from.row, to.row); row += 1) {
        cells.add(`${col}:${row}`);
      }
    }
  });
  return cells;
}

export default function Workbook({ book, compact = false }) {
  if (!book || !book.rows?.length) return null;
  const marked = highlightSet(book.highlight);
  const columns = book.columns || book.rows[0].map((_, index) => String.fromCharCode(65 + index));

  return (
    <View style={styles.frame}>
      <View style={styles.titleBar}>
        <Text style={styles.fileName} numberOfLines={1}>{book.file}</Text>
        <Text style={styles.sheetTab}>{book.sheet}</Text>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View>
          <View style={styles.row}>
            <View style={[styles.rowHead, styles.corner]} />
            {columns.map((letter) => (
              <View key={letter} style={styles.colHead}>
                <Text style={styles.headText}>{letter}</Text>
              </View>
            ))}
          </View>

          <ScrollView
            style={compact ? { maxHeight: 190 } : undefined}
            showsVerticalScrollIndicator={false}
          >
            {book.rows.map((row, rowIndex) => (
              <View key={`r${rowIndex}`} style={styles.row}>
                <View style={styles.rowHead}>
                  <Text style={styles.headText}>{rowIndex + 1}</Text>
                </View>
                {columns.map((_, colIndex) => {
                  const value = row[colIndex] ?? '';
                  const isHeaderRow = rowIndex === 0;
                  const isFormula = String(value).startsWith('=');
                  const isNumber = /^[$\d(-]/.test(String(value)) && !isFormula;
                  const lit = marked.has(`${colIndex}:${rowIndex + 1}`);
                  return (
                    <View
                      key={`c${colIndex}`}
                      style={[styles.cell, lit && styles.cellLit, isHeaderRow && styles.cellHeader]}
                    >
                      <Text
                        numberOfLines={1}
                        style={[
                          styles.cellText,
                          isHeaderRow && styles.cellHeaderText,
                          isFormula && styles.formulaText,
                          isNumber && { textAlign: 'right' },
                        ]}
                      >
                        {String(value)}
                      </Text>
                    </View>
                  );
                })}
              </View>
            ))}
          </ScrollView>
        </View>
      </ScrollView>

      {book.note ? <Text style={styles.note}>{book.note}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    backgroundColor: colors.paper,
  },
  titleBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.ink,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  fileName: { color: colors.paper, fontSize: 13, fontWeight: '600', flexShrink: 1 },
  sheetTab: {
    color: colors.ink,
    backgroundColor: colors.paper,
    fontSize: 11,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginLeft: 8,
  },
  row: { flexDirection: 'row' },
  rowHead: {
    width: ROW_HEAD_WIDTH,
    backgroundColor: colors.canvas,
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.grid,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
  },
  corner: { borderBottomWidth: 1 },
  colHead: {
    width: CELL_WIDTH,
    backgroundColor: colors.canvas,
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.grid,
    alignItems: 'center',
    paddingVertical: 6,
  },
  headText: { fontFamily: mono, fontSize: 11, color: colors.muted },
  cell: {
    width: CELL_WIDTH,
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.grid,
    paddingHorizontal: 6,
    paddingVertical: 8,
    justifyContent: 'center',
  },
  cellLit: { backgroundColor: colors.accentSoft },
  cellHeader: { backgroundColor: '#F6F8FA' },
  cellText: { fontFamily: mono, fontSize: 12, color: colors.ink },
  cellHeaderText: { fontWeight: '700', color: colors.inkSoft },
  formulaText: { color: colors.accent },
  note: {
    fontSize: 12,
    color: colors.muted,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
  },
});
