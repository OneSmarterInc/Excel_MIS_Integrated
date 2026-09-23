import React, { useEffect } from 'react';
import { ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import InteractiveWorkbook from '../../components/InteractiveWorkbook';
import Workbook from '../../components/Workbook';
import { Button, Notice, Stat, Surface } from '../../components/ui';
import { colors, mono, spacing, type } from '../../theme';

export default function ResultScreen({ route, navigation }) {
  const { result, kind, id, title } = route.params;
  const { width } = useWindowDimensions();
  const wide = width >= 760;

  useEffect(() => {
    navigation.setOptions({ title: 'Results' });
  }, [navigation]);

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>{result.percentage}% on this quiz</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>{title}</Text>

      <View style={styles.statRow}>
        <Stat value={result.correct} label="Correct" />
        <Stat value={result.wrong} label="Wrong" />
        <Stat value={`${result.correct}/${result.attempt.total}`} label="Marks" />
        {result.multiple_choice ? (
          <Stat
            value={`${result.multiple_choice.correct}/${result.multiple_choice.total}`}
            label="Multiple choice"
          />
        ) : null}
        {result.business ? (
          <Stat
            value={`${result.business.correct}/${result.business.total}`}
            label="Business questions"
          />
        ) : null}
      </View>

      <Notice
        text={result.summary}
        tone={result.percentage >= 85 ? 'good' : result.percentage >= 60 ? 'info' : 'warn'}
      />

      {result.skills_to_review.length ? (
        <Surface>
          <Text style={type.heading}>Worth another look</Text>
          {result.skills_to_review.map((skill) => (
            <Text key={skill} style={styles.skillLine}>
              {skill}
            </Text>
          ))}
        </Surface>
      ) : null}

      <Text style={[type.heading, { marginTop: spacing(1), marginBottom: spacing(1) }]}>
        Question by question
      </Text>

      {result.questions.map((question) => (
        <Surface key={question.id}>
          <View style={styles.qHead}>
            <Text style={styles.qNumber}>
              Question {question.order}
              {question.kind === 'BUSINESS' ? '  ·  business question' : ''}
            </Text>
            <Text style={[styles.verdict, question.is_correct ? styles.right : styles.wrong]}>
              {question.is_correct ? 'Correct' : 'Wrong'}
            </Text>
          </View>

          <View style={wide ? styles.split : undefined}>
            <View style={wide ? styles.splitLeft : undefined}>
              <Text style={styles.prompt}>{question.prompt}</Text>
              <View style={styles.answerBlock}>
                <Text style={styles.answerLabel}>Your answer</Text>
                <Text style={[styles.answerValue, !question.is_correct && { color: colors.red }]}>
                  {question.your_answer}
                </Text>
              </View>
              {!question.is_correct ? (
                <View style={styles.answerBlock}>
                  <Text style={styles.answerLabel}>Correct answer</Text>
                  <Text style={[styles.answerValue, { color: colors.accent }]}>
                    {question.correct_answer}
                  </Text>
                </View>
              ) : null}
              {question.kind === 'BUSINESS' && question.steps ? (
                <Text style={styles.steps}>How it was done: {question.steps}</Text>
              ) : null}
              <Text style={styles.explanation}>{question.explanation}</Text>
            </View>
            <View style={wide ? styles.splitRight : { marginTop: spacing(1.5) }}>
              {question.kind === 'BUSINESS' ? (
                <InteractiveWorkbook book={question.workbook} readOnly />
              ) : (
                <Workbook book={question.workbook} compact={!wide} />
              )}
            </View>
          </View>
        </Surface>
      ))}

      <Button
        tone="accent"
        label="Retake this section with the next set of questions"
        onPress={() => navigation.replace('Quiz', { kind, id, title })}
        style={{ marginBottom: 8 }}
      />
      <Button tone="quiet" label="Back to the course" onPress={() => navigation.popToTop()} />
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
  statRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing(1) },
  skillLine: { fontSize: 14, color: colors.inkSoft, marginTop: 6 },
  qHead: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  qNumber: { fontFamily: mono, fontSize: 12, color: colors.muted },
  verdict: { fontSize: 12, fontWeight: '700', paddingHorizontal: 8, paddingVertical: 3 },
  right: { color: colors.paper, backgroundColor: colors.accent },
  wrong: { color: colors.paper, backgroundColor: colors.red },
  split: { flexDirection: 'row' },
  splitLeft: { flex: 1, paddingRight: spacing(2) },
  splitRight: { flex: 1.05 },
  prompt: { fontSize: 15, lineHeight: 23, color: colors.ink, marginBottom: 10 },
  answerBlock: { marginBottom: 8 },
  answerLabel: { fontSize: 12, color: colors.muted },
  answerValue: { fontFamily: mono, fontSize: 14, color: colors.ink, marginTop: 2 },
  steps: { fontSize: 13, color: colors.amber, marginBottom: 8, lineHeight: 19 },
  explanation: {
    fontSize: 14,
    lineHeight: 22,
    color: colors.inkSoft,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
    paddingTop: 8,
    marginTop: 4,
  },
});
