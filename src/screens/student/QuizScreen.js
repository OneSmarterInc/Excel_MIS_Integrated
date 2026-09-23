import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from 'react-native';

import api, { readError } from '../../api/client';
import InteractiveWorkbook from '../../components/InteractiveWorkbook';
import Workbook from '../../components/Workbook';
import { Button, Loading, Notice } from '../../components/ui';
import { colors, mono, spacing, type } from '../../theme';

export default function QuizScreen({ route, navigation }) {
  const { kind, id, title } = route.params;
  const { width } = useWindowDimensions();
  const wide = width >= 760;

  const [attempt, setAttempt] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState({});
  const [typed, setTyped] = useState({});
  const [checks, setChecks] = useState({});
  const [checking, setChecking] = useState(false);
  const attemptRef = useRef(null);
  const pendingCheck = useRef(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const start = useCallback(async () => {
    setError('');
    try {
      const body = kind === 'chapter' ? { chapter_id: id } : { module_id: id };
      const { data } = await api.post('/quizzes/start/', body);
      setAttempt(data.attempt);
      attemptRef.current = data.attempt;
      setQuestions(data.questions);
      setCurrent(0);
      setAnswers({});
      setTyped({});
      setChecks({});
    } catch (err) {
      setError(readError(err));
    }
  }, [kind, id]);

  useEffect(() => {
    navigation.setOptions({ title: 'Quiz' });
    start();
  }, [navigation, start]);

  // The student can check a business answer while the paper is still open. The server
  // only says whether it holds up, never what the expected value is.
  const checkAnswer = useCallback(async (questionId, override) => {
    const value = String(override ?? '').trim();
    if (!value || !attemptRef.current) return;
    setChecking(true);
    try {
      const { data } = await api.post(`/quizzes/${attemptRef.current.id}/check/`, {
        question_id: questionId,
        typed_answer: value,
      });
      setChecks((prev) => ({ ...prev, [questionId]: data }));
    } catch (err) {
      setError(readError(err));
    } finally {
      setChecking(false);
    }
  }, []);

  // Whatever lands in the answer cell of the sheet becomes the answer, and it is checked
  // a moment later so the student sees straight away whether the sheet agrees with them.
  const answerCellChanged = useCallback(
    (questionId, value) => {
      setTyped((prev) => (prev[questionId] === value ? prev : { ...prev, [questionId]: value }));
      setChecks((prev) => ({ ...prev, [questionId]: undefined }));
      if (pendingCheck.current) clearTimeout(pendingCheck.current);
      if (!String(value ?? '').trim()) return;
      pendingCheck.current = setTimeout(() => checkAnswer(questionId, value), 700);
    },
    [checkAnswer]
  );

  useEffect(() => () => pendingCheck.current && clearTimeout(pendingCheck.current), []);

  const submit = async () => {
    setBusy(true);
    try {
      const payload = questions.map((question) =>
        question.kind === 'BUSINESS'
          ? { question_id: question.id, typed_answer: typed[question.id] ?? '' }
          : { question_id: question.id, selected_index: answers[question.id] ?? null }
      );
      const { data } = await api.post(`/quizzes/${attempt.id}/submit/`, { answers: payload });
      navigation.replace('Result', { result: data, kind, id, title });
    } catch (err) {
      setError(readError(err));
      setBusy(false);
    }
  };

  if (!attempt && !error) return <Loading label="Building seven fresh questions" />;
  if (error && !questions.length) {
    return (
      <View style={styles.page}>
        <Notice text={error} tone="error" />
        <Button label="Try again" onPress={start} />
      </View>
    );
  }

  const question = questions[current];
  const business = question.kind === 'BUSINESS';
  const answered =
    questions.filter((item) =>
      item.kind === 'BUSINESS'
        ? String(typed[item.id] ?? '').trim() !== ''
        : answers[item.id] !== undefined
    ).length;
  const chosen = answers[question.id];

  const verdict = checks[question.id];

  const placeholder = {
    currency: 'for example 12480 or $12,480.00',
    percent: 'for example 18.5',
    number: 'a whole number',
    text: 'type the name',
  }[question.answer_format] || 'your answer';

  const QuestionBody = business ? (
    <View>
      <View style={styles.businessTag}>
        <Text style={styles.businessTagText}>Business question</Text>
        <Text style={styles.skill}>{question.skill}</Text>
      </View>
      <Text style={styles.prompt}>{question.prompt}</Text>
      <Text style={styles.answerLabel}>
        Your answer
        {question.workbook?.answer_cell
          ? `  ·  read from cell ${question.workbook.answer_cell} of the sheet`
          : ''}
      </Text>
      <View style={styles.answerRow}>
        <TextInput
          value={typed[question.id] ?? ''}
          onChangeText={(value) => {
            setTyped((prev) => ({ ...prev, [question.id]: value }));
            setChecks((prev) => ({ ...prev, [question.id]: undefined }));
          }}
          placeholder={placeholder}
          placeholderTextColor={colors.muted}
          style={styles.answerInput}
          autoCapitalize={question.answer_format === 'text' ? 'words' : 'none'}
          autoCorrect={false}
          keyboardType={question.answer_format === 'text' ? 'default' : 'numbers-and-punctuation'}
          onSubmitEditing={() => checkAnswer(question.id, typed[question.id])}
        />
        <Pressable
          onPress={() => checkAnswer(question.id, typed[question.id])}
          disabled={checking || !String(typed[question.id] ?? '').trim()}
          style={[
            styles.checkButton,
            (checking || !String(typed[question.id] ?? '').trim()) && { opacity: 0.45 },
          ]}
        >
          <Text style={styles.checkButtonText}>{checking ? 'Checking' : 'Check'}</Text>
        </Pressable>
      </View>

      {verdict ? (
        <View style={[styles.verdict, verdict.is_correct ? styles.verdictRight : styles.verdictWrong]}>
          <Text style={styles.verdictMark}>{verdict.is_correct ? '\u2713' : '\u2715'}</Text>
          <Text
            style={[
              styles.verdictText,
              { color: verdict.is_correct ? colors.accent : colors.red },
            ]}
          >
            {verdict.is_correct ? 'Correct. ' : 'Not correct. '}
            {verdict.message}
          </Text>
        </View>
      ) : (
        <Text style={styles.checkHint}>
          {question.workbook?.answer_cell
            ? `Work in the sheet and put your result in ${question.workbook.answer_cell}. It arrives here on its own and is checked for you.`
            : 'Work in the sheet, tap a figure in the status bar to bring it up here, then check it.'}
        </Text>
      )}

      {question.steps ? <Text style={styles.steps}>Hint: {question.steps}</Text> : null}
    </View>
  ) : (
    <View>
      <Text style={styles.skill}>{question.skill}</Text>
      <Text style={styles.prompt}>{question.prompt}</Text>
      {question.options.map((option, index) => {
        const active = chosen === index;
        return (
          <Pressable
            key={option}
            onPress={() => setAnswers((prev) => ({ ...prev, [question.id]: index }))}
            style={[styles.option, active && styles.optionActive]}
          >
            <Text style={[styles.optionLetter, active && { color: colors.paper }]}>
              {String.fromCharCode(65 + index)}
            </Text>
            <Text style={[styles.optionText, active && { color: colors.paper }]}>{option}</Text>
          </Pressable>
        );
      })}
    </View>
  );

  const useValue = (value) => setTyped((prev) => ({ ...prev, [question.id]: value }));

  const SheetPanel = business ? (
    <InteractiveWorkbook
      key={question.id}
      book={question.workbook}
      onUseValue={useValue}
      onAnswerCellChange={(value) => answerCellChanged(question.id, value)}
    />
  ) : (
    <Workbook book={question.workbook} compact={!wide} />
  );

  return (
    <View style={{ flex: 1, backgroundColor: colors.canvas }}>
      <View style={styles.progressBar}>
        {questions.map((item, index) => (
          <Pressable
            key={item.id}
            onPress={() => setCurrent(index)}
            style={[
              styles.pip,
              item.kind === 'BUSINESS' && styles.pipBusiness,
              index === current && styles.pipCurrent,
              (item.kind === 'BUSINESS'
                ? String(typed[item.id] ?? '').trim() !== ''
                : answers[item.id] !== undefined) &&
                index !== current &&
                styles.pipDone,
            ]}
          >
            <Text
              style={[
                styles.pipText,
                (index === current ||
                  (item.kind === 'BUSINESS'
                    ? String(typed[item.id] ?? '').trim() !== ''
                    : answers[item.id] !== undefined)) && { color: colors.paper },
              ]}
            >
              {index + 1}
            </Text>
          </Pressable>
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.page}>
        <Text style={styles.sectionLabel} numberOfLines={1}>{title}</Text>
        <Notice text={error} tone="error" />

        {wide ? (
          <View style={styles.split}>
            <View style={styles.splitLeft}>{QuestionBody}</View>
            <View style={styles.splitRight}>{SheetPanel}</View>
          </View>
        ) : (
          <View>
            {business ? QuestionBody : SheetPanel}
            <View style={{ height: spacing(2) }} />
            {business ? SheetPanel : QuestionBody}
          </View>
        )}

        <View style={styles.navRow}>
          <Button
            tone="quiet"
            label="Previous"
            disabled={current === 0}
            onPress={() => setCurrent((index) => Math.max(0, index - 1))}
            style={{ flex: 1, marginRight: 8 }}
          />
          {current === questions.length - 1 ? (
            <Button
              tone="accent"
              label={busy ? 'Marking' : `Submit ${answered}/${questions.length}`}
              disabled={busy}
              onPress={submit}
              style={{ flex: 1 }}
            />
          ) : (
            <Button
              label="Next"
              onPress={() => setCurrent((index) => Math.min(questions.length - 1, index + 1))}
              style={{ flex: 1 }}
            />
          )}
        </View>
      </ScrollView>
    </View>
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
  progressBar: {
    flexDirection: 'row',
    paddingHorizontal: spacing(2),
    paddingVertical: spacing(1),
    backgroundColor: colors.paper,
    borderBottomWidth: 1,
    borderBottomColor: colors.grid,
  },
  pip: {
    width: 30,
    height: 30,
    borderWidth: 1,
    borderRadius: 8,
    borderColor: colors.gridStrong,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 6,
  },
  pipCurrent: { backgroundColor: colors.accent, borderColor: colors.accent },
  pipDone: { backgroundColor: colors.accent, borderColor: colors.accent },
  pipBusiness: { borderColor: colors.amber, borderWidth: 2 },
  pipText: { fontFamily: mono, fontSize: 12, color: colors.muted },
  sectionLabel: { fontFamily: mono, fontSize: 12, color: colors.muted, marginBottom: spacing(1.5) },
  split: { flexDirection: 'row' },
  splitLeft: { flex: 1, paddingRight: spacing(2) },
  splitRight: { flex: 1.15 },
  skill: { fontFamily: mono, fontSize: 12, color: colors.accent, marginBottom: 6 },
  prompt: { ...type.body, fontSize: 16, lineHeight: 25, marginBottom: spacing(1.5) },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 10,
    borderColor: colors.gridStrong,
    backgroundColor: colors.paper,
    paddingVertical: 12,
    paddingHorizontal: 12,
    marginBottom: 8,
  },
  optionActive: { backgroundColor: colors.accent, borderColor: colors.accent },
  optionLetter: { fontFamily: mono, fontSize: 12, color: colors.muted, width: 22 },
  optionText: { flex: 1, fontSize: 15, color: colors.ink },
  navRow: { flexDirection: 'row', marginTop: spacing(2) },
  businessTag: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  businessTagText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.paper,
    backgroundColor: colors.amber,
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginRight: 10,
  },
  answerLabel: { fontSize: 13, fontWeight: '600', color: colors.inkSoft, marginBottom: 6 },
  answerRow: { flexDirection: 'row', alignItems: 'stretch' },
  answerInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.amber,
    backgroundColor: colors.paper,
    fontFamily: mono,
    fontSize: 16,
    color: colors.ink,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  checkButton: {
    justifyContent: 'center',
    backgroundColor: colors.amber,
    paddingHorizontal: 16,
  },
  checkButtonText: { color: colors.paper, fontWeight: '700', fontSize: 14 },
  checkHint: { fontSize: 12.5, color: colors.muted, marginTop: 8, lineHeight: 18 },
  verdict: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    borderLeftWidth: 4,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginTop: 10,
  },
  verdictRight: { borderLeftColor: colors.accent, backgroundColor: colors.accentSoft },
  verdictWrong: { borderLeftColor: colors.red, backgroundColor: colors.redSoft },
  verdictMark: { fontSize: 16, fontWeight: '700', marginRight: 8, color: colors.ink },
  verdictText: { flex: 1, fontSize: 14, lineHeight: 20 },
  steps: { fontSize: 12.5, color: colors.muted, marginTop: 8, lineHeight: 18 },
});
