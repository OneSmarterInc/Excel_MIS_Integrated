import React, { useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { colors, radius, shadow, spacing, type } from '../theme';

export function Surface({ children, style }) {
  return <View style={[styles.surface, style]}>{children}</View>;
}

export function SectionTitle({ children, note }) {
  return (
    <View style={styles.sectionTitle}>
      <Text style={type.heading}>{children}</Text>
      {note ? <Text style={[type.small, { marginTop: 2 }]}>{note}</Text> : null}
    </View>
  );
}

export function Button({ label, onPress, tone = 'solid', disabled, style }) {
  const tones = {
    solid: { backgroundColor: colors.accent, color: colors.paper, borderColor: colors.accent },
    accent: { backgroundColor: colors.accent, color: colors.paper, borderColor: colors.accent },
    quiet: { backgroundColor: colors.paper, color: colors.ink, borderColor: colors.gridStrong },
    danger: { backgroundColor: colors.redSoft, color: colors.red, borderColor: colors.red },
  };
  const tint = tones[tone] || tones.solid;
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: tint.backgroundColor, borderColor: tint.borderColor },
        (pressed || disabled) && { opacity: 0.65 },
        style,
      ]}
    >
      <Text style={[styles.buttonLabel, { color: tint.color }]}>{label}</Text>
    </Pressable>
  );
}

export function Field({ label, hint, secureTextEntry, ...props }) {
  // A password field gets a show and hide control, because typing a password blind into a
  // phone keyboard is how people end up locked out of their own account.
  const [hidden, setHidden] = useState(true);
  const isPassword = !!secureTextEntry;
  return (
    <View style={{ marginBottom: spacing(2) }}>
      <Text style={styles.label}>{label}</Text>
      <View style={isPassword ? styles.passwordRow : null}>
        <TextInput
          placeholderTextColor={colors.muted}
          style={[styles.input, isPassword && styles.passwordInput]}
          secureTextEntry={isPassword && hidden}
          {...props}
        />
        {isPassword ? (
          <Pressable onPress={() => setHidden((on) => !on)} style={styles.reveal}>
            <Text style={styles.revealText}>{hidden ? 'Show' : 'Hide'}</Text>
          </Pressable>
        ) : null}
      </View>
      {hint ? <Text style={[type.small, { marginTop: 4 }]}>{hint}</Text> : null}
    </View>
  );
}

/**
 * A yes or no question in front of anything that cannot be undone.
 *
 * Alert.alert does nothing on the web build, so this is a plain modal that behaves the
 * same on a laptop and on a phone.
 */
export function ConfirmDialog({ visible, title, message, confirmLabel = 'Yes', cancelLabel = 'No',
                                tone = 'danger', onConfirm, onCancel }) {
  return (
    <Modal visible={!!visible} transparent animationType="fade" onRequestClose={onCancel}>
      <Pressable style={styles.backdrop} onPress={onCancel}>
        <Pressable style={styles.dialog} onPress={() => {}}>
          <Text style={styles.dialogTitle}>{title}</Text>
          {message ? <Text style={styles.dialogBody}>{message}</Text> : null}
          <View style={styles.dialogRow}>
            <Button
              tone="quiet"
              label={cancelLabel}
              onPress={onCancel}
              style={{ flex: 1, marginRight: 8 }}
            />
            <Button tone={tone} label={confirmLabel} onPress={onConfirm} style={{ flex: 1 }} />
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

export function Choice({ options, value, onChange }) {
  return (
    <View style={styles.choiceRow}>
      {options.map((option) => {
        const active = option.value === value;
        return (
          <Pressable
            key={option.value}
            onPress={() => onChange(option.value)}
            style={[styles.choice, active && styles.choiceActive]}
          >
            <Text style={[styles.choiceLabel, active && { color: colors.tabActiveText }]}>
              {option.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Notice({ text, tone = 'info' }) {
  if (!text) return null;
  const tint = {
    info: { bg: colors.canvas, border: colors.gridStrong, fg: colors.ink },
    error: { bg: colors.redSoft, border: colors.red, fg: colors.red },
    good: { bg: colors.accentSoft, border: colors.accent, fg: colors.accent },
    warn: { bg: colors.amberSoft, border: colors.amber, fg: colors.amber },
  }[tone];
  return (
    <View style={[styles.notice, { backgroundColor: tint.bg, borderLeftColor: tint.border }]}>
      <Text style={{ color: tint.fg, fontSize: 14, lineHeight: 21 }}>{text}</Text>
    </View>
  );
}

export function Loading({ label = 'Loading' }) {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.ink} />
      <Text style={[type.small, { marginTop: spacing(1) }]}>{label}</Text>
    </View>
  );
}

export function Empty({ title, body, action }) {
  return (
    <Surface style={{ alignItems: 'flex-start' }}>
      <Text style={type.heading}>{title}</Text>
      <Text style={[type.body, { marginTop: 6, color: colors.inkSoft }]}>{body}</Text>
      {action}
    </Surface>
  );
}

export function Stat({ value, label, tone = 'plain' }) {
  const tint = {
    plain: {},
    good: { backgroundColor: colors.accentSoft, borderColor: '#CFE6DA' },
    warn: { backgroundColor: colors.amberSoft, borderColor: '#F2E0C4' },
  }[tone];
  return (
    <View style={[styles.stat, tint]}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={type.small}>{label}</Text>
    </View>
  );
}

/** A page heading with its one line of context underneath. */
export function PageTitle({ children, note }) {
  return (
    <View style={{ marginBottom: spacing(2.5) }}>
      <Text style={type.title}>{children}</Text>
      {note ? <Text style={[type.small, { marginTop: 4 }]}>{note}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  surface: {
    backgroundColor: colors.paper,
    borderWidth: 1,
    borderColor: colors.grid,
    borderRadius: radius.card,
    padding: spacing(2.25),
    marginBottom: spacing(1.5),
    ...shadow,
  },
  sectionTitle: { marginBottom: spacing(1), marginTop: spacing(1) },
  button: {
    borderWidth: 1,
    paddingVertical: 13,
    paddingHorizontal: 20,
    borderRadius: radius.control,
    alignItems: 'center',
  },
  buttonLabel: { fontSize: 15, fontWeight: '600' },
  label: { fontSize: 13, fontWeight: '600', color: colors.inkSoft, marginBottom: 6 },
  passwordRow: { flexDirection: 'row', alignItems: 'center' },
  passwordInput: { flex: 1 },
  reveal: {
    paddingHorizontal: 12,
    paddingVertical: 12,
    marginLeft: 8,
    borderWidth: 1,
    borderColor: colors.gridStrong,
    borderRadius: radius.control,
    backgroundColor: colors.paper,
  },
  revealText: { fontSize: 13, fontWeight: '600', color: colors.accent },
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(11,31,23,0.45)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing(3),
  },
  dialog: {
    backgroundColor: colors.paper,
    borderRadius: radius.card,
    padding: spacing(3),
    width: '100%',
    maxWidth: 420,
  },
  dialogTitle: { fontSize: 18, fontWeight: '700', color: colors.ink },
  dialogBody: { fontSize: 14.5, lineHeight: 21, color: colors.inkSoft, marginTop: 8 },
  dialogRow: { flexDirection: 'row', marginTop: spacing(2.5) },
  input: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    backgroundColor: colors.paper,
    borderRadius: radius.control,
    paddingHorizontal: 13,
    paddingVertical: 12,
    fontSize: 15,
    color: colors.ink,
  },
  choiceRow: { flexDirection: 'row', marginBottom: spacing(2) },
  choice: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.grid,
    backgroundColor: colors.paper,
    borderRadius: radius.control,
    paddingVertical: 12,
    alignItems: 'center',
    marginRight: 8,
  },
  choiceActive: { backgroundColor: colors.tabActive, borderColor: colors.tabActive },
  choiceLabel: { fontSize: 14, fontWeight: '600', color: colors.inkSoft },
  notice: {
    borderLeftWidth: 4,
    borderRadius: radius.control,
    padding: spacing(1.5),
    marginBottom: spacing(1.5),
  },
  center: { paddingVertical: spacing(4), alignItems: 'center' },
  stat: {
    flexGrow: 1,
    flexBasis: 170,
    borderWidth: 1,
    borderColor: colors.grid,
    backgroundColor: colors.paper,
    borderRadius: radius.card,
    padding: spacing(2),
    marginRight: 8,
    marginBottom: 8,
    ...shadow,
  },
  statValue: { fontSize: 26, fontWeight: '700', color: colors.ink, marginBottom: 2 },
});
