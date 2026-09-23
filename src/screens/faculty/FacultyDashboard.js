import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import api, { readError } from '../../api/client';
import { Empty, Loading, Notice, Stat, Surface } from '../../components/ui';
import { useAuth } from '../../store/auth';
import { colors, mono, spacing, type } from '../../theme';

function Bar({ percentage }) {
  const width = Math.max(2, Math.min(100, percentage ?? 0));
  const tone = percentage >= 75 ? colors.accent : percentage >= 50 ? colors.amber : colors.red;
  return (
    <View style={styles.barTrack}>
      <View style={[styles.barFill, { width: `${width}%`, backgroundColor: tone }]} />
    </View>
  );
}

export default function FacultyDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data: payload } = await api.get('/faculty/dashboard/');
      setData(payload);
      setError('');
    } catch (err) {
      setError(readError(err));
    } finally {
      setRefreshing(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  if (!data && !error) return <Loading label="Reading your courses" />;

  return (
    <ScrollView
      style={{ backgroundColor: colors.canvas }}
      contentContainerStyle={styles.page}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load(); }} />
      }
    >
      <Text style={type.title}>Dashboard</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Enrolment and quiz results across everything you teach, {user?.name}.
      </Text>

      <Notice text={error} tone="error" />

      {data ? (
        <>
          <View style={styles.statRow}>
            <Stat value={data.totals.courses} label="Courses" />
            <Stat value={data.totals.students} label="Students enrolled" />
            <Stat value={data.totals.quizzes_taken} label="Quizzes taken" tone="good" />
            <Stat
              value={
                data.totals.average_percentage === null
                  ? '—'
                  : `${data.totals.average_percentage}%`
              }
              label={data.totals.marks ? `Average mark (${data.totals.marks})` : 'Average mark'}
              tone="warn"
            />
          </View>

          {data.courses.length === 0 ? (
            <Empty
              title="No courses yet"
              body="Open Course in the sidebar, give it a code and a name, then upload the book you teach from."
            />
          ) : (
            data.courses.map((course) => (
              <Surface key={course.course_id}>
                <View style={styles.courseHead}>
                  <Text style={styles.code}>{course.code}</Text>
                  <Text style={styles.courseName} numberOfLines={1}>{course.name}</Text>
                </View>
                <View style={styles.metaRow}>
                  <Text style={styles.meta}>{course.students_enrolled} enrolled</Text>
                  <Text style={styles.meta}>{course.chapters} chapters</Text>
                  <Text style={styles.meta}>{course.modules} modules</Text>
                  <Text style={styles.meta}>{course.quizzes_taken} quizzes taken</Text>
                </View>
                {course.average_percentage === null ? (
                  <Text style={styles.avgLabel}>
                    No quiz has been submitted on this course yet.
                  </Text>
                ) : (
                  <>
                    <Text style={styles.avgLabel}>
                      Course average {course.average_percentage}% on {course.marks} marks
                    </Text>
                    <Bar percentage={course.average_percentage} />
                  </>
                )}
              </Surface>
            ))
          )}
        </>
      ) : null}
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
  statRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing(1.5) },
  courseHead: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  code: {
    fontFamily: mono,
    fontSize: 12,
    color: colors.accent,
    backgroundColor: colors.accentSoft,
    paddingHorizontal: 8,
    paddingVertical: 4,
    marginRight: 10,
  },
  courseName: { flex: 1, fontSize: 16, fontWeight: '600', color: colors.ink },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 10 },
  meta: { fontSize: 13, color: colors.muted, marginRight: 14 },
  avgLabel: { fontSize: 13, color: colors.inkSoft, marginBottom: 6 },
  barTrack: {
    height: 8,
    backgroundColor: colors.grid,
    borderRadius: 999,
    overflow: 'hidden',
  },
  barFill: { height: '100%', borderRadius: 999 },
});
