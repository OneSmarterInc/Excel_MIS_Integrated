import React, { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, useWindowDimensions, View }
  from 'react-native';

import api, { readError } from '../../api/client';
import Workbook from '../../components/Workbook';
import { Button, Loading, Notice, Surface } from '../../components/ui';
import { colors, mono, spacing, type } from '../../theme';

export default function QuizPreview({ route, navigation }) {
  const { kind, id, title } = route.params;
  const { width } = useWindowDimensions();
  const wide = width >= 760;
  const [sets, setSets] = useState(null);
  const [current, setCurrent] = useState(1);
  const [editing, setEditing] = useState(null);
  const [draft, setDraft] = useState({});
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const query = kind === 'chapter' ? `chapter_id=${id}` : `module_id=${id}`;

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/quizzes/sets/?${query}`);
      setSets(data.sets);
      setError('');
    } catch (err) {
      setError(readError(err));
      setSets([]);
    }
  }, [query]);

  useEffect(() => {
    navigation.setOptions({ title: 'Question sets' });
    load();
  }, [load, navigation]);

  const rebuild = async () => {
    setBusy(true);
    setMessage('');
    try {
      const body = kind === 'chapter' ? { chapter_id: id } : { module_id: id };
      const { data } = await api.post('/quizzes/sets/', body);
      setSets(data.sets);
      setMessage('All five sets rebuilt. Any wording you had written is gone.');
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const startEditing = (question) => {
    setEditing(question.id);
    setDraft({
      prompt: question.prompt,
      options: [...(question.options || [])],
      correct_index: question.correct_index,
      expected_answer: question.expected_answer,
      explanation: question.explanation,
    });
  };

  const save = async (question) => {
    setBusy(true);
    setMessage('');
    setError('');
    try {
      const body = question.kind === 'BUSINESS'
        ? { prompt: draft.prompt, expected_answer: draft.expected_answer,
            explanation: draft.explanation }
        : { prompt: draft.prompt, options: draft.options,
            correct_index: draft.correct_index, explanation: draft.explanation };
      await api.patch(`/quizzes/sets/questions/${question.id}/`, body);
      setEditing(null);
      setMessage('Saved. Students who sit this set next will see the new wording.');
      load();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  if (!sets) return <Loading label="Loading the five sets" />;

  const active = sets.find((item) => item.number === current) || sets[0];
  const questions = active ? active.questions : [];

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Question sets</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        {title}. These are the only five sets for this section, and every other chapter and
        module has its own five. All five ask the same skills in the same order, so they are
        level with each other and only the figures differ. Students are handed them in turn,
        and a retake moves a student on to the next set. Edit anything here and the next
        student to sit that set sees your wording.
      </Text>
      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      <View style={styles.tabRow}>
        {sets.map((item) => (
          <Pressable
            key={item.id}
            onPress={() => { setCurrent(item.number); setEditing(null); }}
            style={[styles.tab, current === item.number && styles.tabActive]}
          >
            <Text
              style={[styles.tabText, current === item.number && { color: colors.tabActiveText }]}
            >
              {item.label}
            </Text>
            <Text style={styles.tabMeta}>
              {item.students_using_it} student{item.students_using_it === 1 ? '' : 's'}
            </Text>
          </Pressable>
        ))}
      </View>

      {questions.map((question) => (
        <Surface key={question.id}>
          <View style={styles.qHead}>
            <Text style={styles.qNumber}>
              Question {question.order}  ·  {question.skill}
              {question.kind === 'BUSINESS' ? '  ·  typed answer' : ''}
            </Text>
            <Pressable onPress={() => (editing === question.id
              ? setEditing(null)
              : startEditing(question))}>
              <Text style={styles.editLink}>
                {editing === question.id ? 'Cancel' : 'Edit'}
              </Text>
            </Pressable>
          </View>
          <View style={wide ? styles.splitRow : undefined}>
            <View style={wide ? styles.splitLeft : undefined}>
              {editing === question.id ? (
                <View>
                  <TextInput
                    value={draft.prompt}
                    onChangeText={(value) => setDraft((d) => ({ ...d, prompt: value }))}
                    multiline
                    style={styles.editor}
                  />
                  {question.kind === 'BUSINESS' ? (
                    <TextInput
                      value={String(draft.expected_answer ?? '')}
                      onChangeText={(value) =>
                        setDraft((d) => ({ ...d, expected_answer: value }))}
                      style={styles.smallEditor}
                      placeholder="Expected answer"
                      placeholderTextColor={colors.muted}
                    />
                  ) : (
                    (draft.options || []).map((option, index) => (
                      <View key={index} style={styles.optionEditRow}>
                        <Pressable
                          onPress={() => setDraft((d) => ({ ...d, correct_index: index }))}
                          style={[styles.mark, draft.correct_index === index && styles.markOn]}
                        >
                          <Text style={[styles.markText,
                                        draft.correct_index === index && { color: colors.paper }]}>
                            {String.fromCharCode(65 + index)}
                          </Text>
                        </Pressable>
                        <TextInput
                          value={option}
                          onChangeText={(value) => setDraft((d) => {
                            const options = [...d.options];
                            options[index] = value;
                            return { ...d, options };
                          })}
                          style={styles.smallEditor}
                        />
                      </View>
                    ))
                  )}
                  <TextInput
                    value={draft.explanation}
                    onChangeText={(value) => setDraft((d) => ({ ...d, explanation: value }))}
                    multiline
                    style={styles.editor}
                    placeholder="Why the correct answer is correct"
                    placeholderTextColor={colors.muted}
                  />
                  <Button
                    label={busy ? 'Saving' : 'Save this question'}
                    disabled={busy}
                    onPress={() => save(question)}
                  />
                </View>
              ) : (
              <View>
              <Text style={styles.prompt}>{question.prompt}</Text>
              {question.kind === 'BUSINESS' ? (
                <View style={styles.expected}>
                  <Text style={styles.expectedLabel}>Expected answer</Text>
                  <Text style={styles.expectedValue}>{question.expected_display}</Text>
                  <Text style={styles.expectedSteps}>{question.steps}</Text>
                </View>
              ) : null}
              {(question.options || []).map((option, index) => (
                <View
                  key={option}
                  style={[styles.option, index === question.correct_index && styles.optionCorrect]}
                >
                  <Text style={styles.optionLetter}>{String.fromCharCode(65 + index)}</Text>
                  <Text style={styles.optionText}>{option}</Text>
                </View>
              ))}
              <Text style={styles.explanation}>{question.explanation}</Text>
              </View>
              )}
            </View>
            <View style={wide ? styles.splitRight : { marginTop: spacing(1.5) }}>
              <Workbook book={question.workbook} compact={!wide} />
            </View>
          </View>
        </Surface>
      ))}

      <Button
        tone="quiet"
        label={busy ? 'Rebuilding' : 'Rebuild all five sets'}
        disabled={busy}
        onPress={rebuild}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    padding: spacing(2.5),
    paddingBottom: spacing(6),
    width: '100%',
    maxWidth: 1140,
    alignSelf: 'center',
  },
  qNumber: { fontFamily: mono, fontSize: 12, color: colors.accent, marginBottom: 8 },
  qHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  editLink: { fontSize: 13.5, fontWeight: '700', color: colors.accent },
  tabRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing(1.5) },
  tab: {
    borderWidth: 1,
    borderColor: colors.grid,
    backgroundColor: colors.paper,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 9,
    marginRight: 8,
    marginBottom: 8,
    alignItems: 'center',
  },
  tabActive: { backgroundColor: colors.tabActive, borderColor: colors.tabActive },
  tabText: { fontSize: 14, fontWeight: '700', color: colors.inkSoft },
  tabMeta: { fontSize: 11, color: colors.muted, marginTop: 2 },
  editor: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    borderRadius: 10,
    minHeight: 80,
    padding: 10,
    marginBottom: 8,
    fontSize: 14,
    lineHeight: 20,
    color: colors.ink,
    textAlignVertical: 'top',
  },
  smallEditor: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.gridStrong,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 9,
    marginBottom: 8,
    fontSize: 14,
    color: colors.ink,
  },
  optionEditRow: { flexDirection: 'row', alignItems: 'center' },
  mark: {
    width: 30,
    height: 30,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.gridStrong,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
    marginBottom: 8,
  },
  markOn: { backgroundColor: colors.accent, borderColor: colors.accent },
  markText: { fontFamily: mono, fontSize: 12, color: colors.inkSoft },
  splitRow: { flexDirection: 'row' },
  splitLeft: { flex: 1, paddingRight: spacing(2) },
  splitRight: { flex: 1.05 },
  prompt: { fontSize: 15, lineHeight: 23, color: colors.ink, marginBottom: 10 },
  option: {
    flexDirection: 'row',
    borderWidth: 1,
    borderColor: colors.grid,
    paddingVertical: 9,
    paddingHorizontal: 10,
    marginBottom: 6,
    alignItems: 'center',
  },
  optionCorrect: { borderColor: colors.accent, backgroundColor: colors.accentSoft },
  optionLetter: { fontFamily: mono, fontSize: 12, color: colors.muted, width: 20 },
  optionText: { flex: 1, fontSize: 14, color: colors.ink },
  explanation: { fontSize: 13, lineHeight: 20, color: colors.inkSoft, marginTop: 6 },
  expected: {
    borderLeftWidth: 3,
    borderLeftColor: colors.amber,
    backgroundColor: colors.amberSoft,
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: 8,
  },
  expectedLabel: { fontSize: 11, color: colors.muted },
  expectedValue: { fontFamily: mono, fontSize: 15, color: colors.ink, marginTop: 2 },
  expectedSteps: { fontSize: 12.5, color: colors.inkSoft, marginTop: 4, lineHeight: 18 },
});
