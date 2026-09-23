import { useFocusEffect } from '@react-navigation/native';
import React, { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import api, { readError } from '../../api/client';
import { Button, Empty, Loading, Notice, Stat, Surface } from '../../components/ui';
import { colors, mono, radius, spacing, type } from '../../theme';

const STATUS_LABEL = {
  DRAFT: 'Draft',
  UNDER_REVIEW: 'Under review',
  CHANGES: 'Changes requested',
  APPROVED: 'Approved',
  PUBLISHED: 'Published',
};

function StatusChip({ status }) {
  const tint = {
    DRAFT: { bg: colors.canvas, fg: colors.muted },
    UNDER_REVIEW: { bg: colors.amberSoft, fg: colors.amber },
    CHANGES: { bg: colors.redSoft, fg: colors.red },
    APPROVED: { bg: colors.accentSoft, fg: colors.accent },
    PUBLISHED: { bg: colors.accent, fg: colors.paper },
  }[status] || { bg: colors.canvas, fg: colors.muted };
  return (
    <Text style={[styles.chip, { backgroundColor: tint.bg, color: tint.fg }]}>
      {STATUS_LABEL[status] || status}
    </Text>
  );
}

function Row({ label, value }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel} numberOfLines={1}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

// ------------------------------------------------------------------------ dashboard

export function AdminDashboard({ navigation }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data: payload } = await api.get('/admin/dashboard/');
      setData(payload);
      setError('');
    } catch (err) {
      setError(readError(err));
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));
  if (!data && !error) return <Loading label="Reading the platform" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Admin dashboard</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Everything on the platform, and what is waiting on you.
      </Text>
      <Notice text={error} tone="error" />

      {data ? (
        <>
          <View style={styles.statRow}>
            <Stat value={data.totals.users} label="Users" />
            <Stat value={data.totals.students} label="Students" />
            <Stat value={data.totals.instructors} label="Instructors" />
            <Stat value={data.totals.courses} label="Courses" tone="good" />
            <Stat value={data.totals.books} label="Books" />
            <Stat value={data.totals.chapters} label="Chapters" />
            <Stat value={data.totals.modules} label="Modules" />
            <Stat value={data.totals.quiz_submissions} label="Quiz submissions" />
            <Stat
              value={data.totals.average_percentage === null
                ? '—' : `${data.totals.average_percentage}%`}
              label={data.totals.marks ? `Average (${data.totals.marks})` : 'Average mark'}
              tone="warn"
            />
          </View>

          <Surface>
            <Text style={type.heading}>Chapters by status</Text>
            {Object.entries(data.chapters_by_status).map(([key, count]) => (
              <View key={key} style={styles.statusRow}>
                <StatusChip status={key} />
                <Text style={styles.rowValue}>{count}</Text>
              </View>
            ))}
          </Surface>

          <Text style={[type.heading, { marginBottom: spacing(1) }]}>Waiting for review</Text>
          {data.waiting_for_review.length === 0 ? (
            <Empty title="Nothing to review" body="No instructor has submitted a chapter." />
          ) : (
            data.waiting_for_review.map((chapter) => (
              <Pressable key={chapter.id} onPress={() => navigation.navigate('Review')}>
                <Surface>
                  <View style={styles.head}>
                    <Text style={styles.code}>{chapter.course_code}</Text>
                    <StatusChip status={chapter.status} />
                  </View>
                  <Text style={styles.title}>
                    Chapter {chapter.number}: {chapter.title}
                  </Text>
                  <Text style={type.small}>
                    {chapter.instructor} · {chapter.quality.modules} modules ·{' '}
                    {chapter.quality.characters.toLocaleString()} characters
                  </Text>
                </Surface>
              </Pressable>
            ))
          )}
        </>
      ) : null}
    </ScrollView>
  );
}

// ----------------------------------------------------------------------------- users

export function AdminUsers() {
  const [people, setPeople] = useState(null);
  const [role, setRole] = useState('');
  const [search, setSearch] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const query = [role ? `role=${role}` : '', search ? `q=${encodeURIComponent(search)}` : '']
        .filter(Boolean).join('&');
      const { data } = await api.get(`/admin/users/${query ? `?${query}` : ''}`);
      setPeople(data);
      setError('');
    } catch (err) {
      setError(readError(err));
      setPeople([]);
    }
  }, [role, search]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const setRoleOf = async (person, next) => {
    setMessage('');
    try {
      await api.patch(`/admin/users/${person.id}/`, { role: next });
      setMessage(`${person.name} is now ${next.toLowerCase()}.`);
      load();
    } catch (err) {
      setError(readError(err));
    }
  };

  const setActive = async (person, active) => {
    try {
      await api.patch(`/admin/users/${person.id}/`, { is_active: active });
      setMessage(`${person.name} ${active ? 'can sign in again' : 'is suspended'}.`);
      load();
    } catch (err) {
      setError(readError(err));
    }
  };

  if (!people) return <Loading label="Loading accounts" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Users</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Students, instructors and admins. Change a role or suspend an account.
      </Text>
      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      <TextInput
        value={search}
        onChangeText={setSearch}
        placeholder="Search by name or email"
        placeholderTextColor={colors.muted}
        style={styles.search}
        autoCapitalize="none"
      />
      <View style={styles.filterRow}>
        {['', 'STUDENT', 'FACULTY', 'ADMIN'].map((value) => (
          <Pressable
            key={value || 'all'}
            onPress={() => setRole(value)}
            style={[styles.filter, role === value && styles.filterActive]}
          >
            <Text style={[styles.filterText, role === value && { color: colors.tabActiveText }]}>
              {value === '' ? 'Everyone' : value[0] + value.slice(1).toLowerCase()}
            </Text>
          </Pressable>
        ))}
      </View>

      {people.length === 0 ? (
        <Empty title="Nobody here" body="No account matches that filter." />
      ) : (
        people.map((person) => (
          <Surface key={person.id}>
            <View style={styles.head}>
              <Text style={styles.title}>{person.name}</Text>
              <Text style={styles.chipQuiet}>{person.role}</Text>
            </View>
            <Text style={styles.email}>{person.email}</Text>
            <Text style={type.small}>
              {person.role === 'FACULTY'
                ? `${person.courses_taught} courses taught`
                : person.role === 'STUDENT'
                ? `${person.courses_joined} courses joined`
                : 'Platform administrator'}
              {person.is_active ? '' : ' · suspended'}
            </Text>
            <View style={styles.actionRow}>
              {['STUDENT', 'FACULTY', 'ADMIN']
                .filter((value) => value !== person.role)
                .map((value) => (
                  <Pressable key={value} onPress={() => setRoleOf(person, value)}
                             style={styles.action}>
                    <Text style={styles.actionText}>Make {value.toLowerCase()}</Text>
                  </Pressable>
                ))}
              <Pressable onPress={() => setActive(person, !person.is_active)}
                         style={styles.action}>
                <Text style={styles.actionText}>
                  {person.is_active ? 'Suspend' : 'Restore'}
                </Text>
              </Pressable>
            </View>
          </Surface>
        ))
      )}
    </ScrollView>
  );
}

// --------------------------------------------------------------------- courses & books

export function AdminCourses({ navigation }) {
  const [courses, setCourses] = useState(null);
  const [books, setBooks] = useState([]);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [courseList, bookList] = await Promise.all([
        api.get('/admin/courses/'),
        api.get('/admin/books/'),
      ]);
      setCourses(courseList.data);
      setBooks(bookList.data);
      setError('');
    } catch (err) {
      setError(readError(err));
      setCourses([]);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));
  if (!courses) return <Loading label="Loading courses" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Courses and books</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Every course on the platform, and what each book turned into.
      </Text>
      <Notice text={error} tone="error" />

      {courses.map((course) => (
        <Surface key={course.id}>
          <View style={styles.head}>
            <Text style={styles.code}>{course.code}</Text>
            <Text style={type.small}>{course.students} enrolled</Text>
          </View>
          <Text style={styles.title}>{course.name}</Text>
          <Text style={type.small}>
            {course.instructor} · {course.books} books · {course.chapters} chapters
          </Text>
        </Surface>
      ))}

      <Text style={[type.heading, { marginTop: spacing(1), marginBottom: spacing(1) }]}>
        Uploaded and generated books
      </Text>
      {books.length === 0 ? (
        <Empty title="No books yet" body="Nothing has been uploaded or generated." />
      ) : (
        books.map((book) => (
          <Pressable
            key={book.id}
            onPress={() => navigation.navigate('Review', { bookId: book.id })}
          >
            <Surface>
              <View style={styles.head}>
                <Text style={styles.title} numberOfLines={1}>{book.title}</Text>
                <Text style={styles.chipQuiet}>{book.source}</Text>
              </View>
              <Text style={type.small}>
                {book.course_code} · {book.instructor} · {book.kind.toUpperCase()} ·{' '}
                {book.characters.toLocaleString()} characters
              </Text>
              <Text style={styles.note}>{book.extraction_note}</Text>
              <Row label="Chapters" value={`${book.chapters}`} />
              <Row label="Modules" value={`${book.modules}`} />
              <Row label="Published" value={`${book.published_chapters}`} />
              <Row label="Waiting for review" value={`${book.waiting}`} />
            </Surface>
          </Pressable>
        ))
      )}
    </ScrollView>
  );
}

// ---------------------------------------------------------------------------- review

export function AdminReview({ route }) {
  const bookId = route?.params?.bookId;
  const [chapters, setChapters] = useState(null);
  const [filter, setFilter] = useState('UNDER_REVIEW');
  const [open, setOpen] = useState(null);
  const [comment, setComment] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = bookId
        ? await api.get(`/admin/books/${bookId}/`)
        : await api.get(`/admin/review/?status=${filter}`);
      setChapters(bookId ? data.chapters : data);
      setError('');
    } catch (err) {
      setError(readError(err));
      setChapters([]);
    }
  }, [filter, bookId]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const decide = async (chapter, decision) => {
    setBusy(true);
    setMessage('');
    setError('');
    try {
      const { data } = await api.post(`/admin/review/${chapter.id}/`, {
        decision, comment: comment.trim(),
      });
      setMessage(`Chapter ${data.number} is now ${STATUS_LABEL[data.status].toLowerCase()}.`);
      setComment('');
      load();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  if (!chapters) return <Loading label="Loading the queue" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Content review</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Book, chapter and module, with a completeness read on each chapter.
      </Text>
      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      {bookId ? null : (
        <View style={styles.filterRow}>
          {['UNDER_REVIEW', 'CHANGES', 'APPROVED', 'PUBLISHED', 'DRAFT', 'ALL'].map((value) => (
            <Pressable
              key={value}
              onPress={() => setFilter(value)}
              style={[styles.filter, filter === value && styles.filterActive]}
            >
              <Text style={[styles.filterText, filter === value && { color: colors.tabActiveText }]}>
                {value === 'ALL' ? 'All' : STATUS_LABEL[value]}
              </Text>
            </Pressable>
          ))}
        </View>
      )}

      {chapters.length === 0 ? (
        <Empty title="Nothing here" body="No chapter is sitting in this state right now." />
      ) : (
        chapters.map((chapter) => {
          const expanded = open === chapter.id;
          return (
            <Surface key={chapter.id}>
              <Pressable onPress={() => setOpen(expanded ? null : chapter.id)}>
                <View style={styles.head}>
                  <Text style={styles.code}>{chapter.course_code}</Text>
                  <StatusChip status={chapter.status} />
                </View>
                <Text style={styles.title}>
                  Chapter {chapter.number}: {chapter.title}
                </Text>
                <Text style={type.small}>
                  {chapter.instructor} · {chapter.book_title} · {chapter.book_source}
                </Text>
              </Pressable>

              <View style={styles.quality}>
                <Text style={styles.qualityText}>
                  {chapter.quality.modules} modules · {chapter.quality.characters.toLocaleString()}{' '}
                  characters · {chapter.quality.resources} resources ·{' '}
                  {chapter.quality.demonstrations} walkthroughs
                </Text>
                <Text style={[styles.qualityText,
                              { color: chapter.quality.complete ? colors.accent : colors.amber }]}>
                  {chapter.quality.complete
                    ? 'Every module has enough text to teach from.'
                    : `Thin: ${chapter.quality.thin_modules.join(', ') || 'no modules at all'}`}
                </Text>
              </View>

              {chapter.review_comment ? (
                <Text style={styles.note}>Last comment: {chapter.review_comment}</Text>
              ) : null}

              {expanded ? (
                <>
                  {chapter.modules.map((module) => (
                    <View key={module.id} style={styles.moduleRow}>
                      <Text style={styles.moduleNumber}>{module.number}</Text>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.moduleTitle}>{module.title}</Text>
                        <Text style={type.small}>
                          {module.characters.toLocaleString()} characters ·{' '}
                          {module.has_explanation ? 'explained' : 'no explanation yet'} ·{' '}
                          {module.resources} resources
                        </Text>
                      </View>
                    </View>
                  ))}

                  <TextInput
                    value={comment}
                    onChangeText={setComment}
                    placeholder="What has to change, in your own words"
                    placeholderTextColor={colors.muted}
                    multiline
                    style={styles.commentBox}
                  />
                  <View style={styles.actionRow}>
                    <Button
                      tone="accent"
                      label="Approve"
                      disabled={busy}
                      onPress={() => decide(chapter, 'approve')}
                      style={{ flex: 1, marginRight: 8 }}
                    />
                    <Button
                      tone="quiet"
                      label="Request changes"
                      disabled={busy}
                      onPress={() => decide(chapter, 'request_changes')}
                      style={{ flex: 1, marginRight: 8 }}
                    />
                    <Button
                      tone="danger"
                      label="Reject"
                      disabled={busy}
                      onPress={() => decide(chapter, 'reject')}
                      style={{ flex: 1 }}
                    />
                  </View>

                  {chapter.notes?.length ? (
                    <View style={styles.history}>
                      <Text style={type.small}>History</Text>
                      {chapter.notes.map((note) => (
                        <Text key={note.id} style={styles.historyLine}>
                          {note.action} · {note.author_name || 'system'}
                          {note.comment ? ` · ${note.comment}` : ''}
                        </Text>
                      ))}
                    </View>
                  ) : null}
                </>
              ) : null}
            </Surface>
          );
        })
      )}
    </ScrollView>
  );
}

// -------------------------------------------------------------------------- analytics

export function AdminAnalytics() {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState('courses');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data: payload } = await api.get('/admin/analytics/');
      setData(payload);
      setError('');
    } catch (err) {
      setError(readError(err));
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));
  if (!data && !error) return <Loading label="Working out the numbers" />;

  const percent = (value) => (value === null || value === undefined ? '—' : `${value}%`);

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Analytics</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Courses, instructors, students and the modules people struggle with.
      </Text>
      <Notice text={error} tone="error" />

      <View style={styles.filterRow}>
        {['courses', 'instructors', 'students', 'modules', 'skills'].map((value) => (
          <Pressable
            key={value}
            onPress={() => setTab(value)}
            style={[styles.filter, tab === value && styles.filterActive]}
          >
            <Text style={[styles.filterText, tab === value && { color: colors.tabActiveText }]}>
              {value[0].toUpperCase() + value.slice(1)}
            </Text>
          </Pressable>
        ))}
      </View>

      {data && tab === 'courses' ? data.courses.map((row) => (
        <Surface key={row.course_id}>
          <View style={styles.head}>
            <Text style={styles.code}>{row.code}</Text>
            <Text style={styles.big}>{percent(row.average_percentage)}</Text>
          </View>
          <Text style={styles.title}>{row.name}</Text>
          <Text style={type.small}>{row.instructor}</Text>
          <Row label="Students" value={`${row.students}`} />
          <Row label="Quiz attempts" value={`${row.attempts}`} />
          <Row label="Published chapters" value={`${row.published_chapters} of ${row.chapters}`} />
        </Surface>
      )) : null}

      {data && tab === 'instructors' ? data.instructors.map((row) => (
        <Surface key={row.id}>
          <View style={styles.head}>
            <Text style={styles.title}>{row.name}</Text>
            <Text style={styles.big}>{percent(row.average_percentage)}</Text>
          </View>
          <Text style={styles.email}>{row.email}</Text>
          <Row label="Courses" value={`${row.courses}`} />
          <Row label="Students" value={`${row.students}`} />
          <Row label="Chapters published" value={`${row.chapters_published}`} />
          <Row label="Waiting on review" value={`${row.chapters_waiting}`} />
        </Surface>
      )) : null}

      {data && tab === 'students' ? data.students.map((row) => (
        <Surface key={row.id}>
          <View style={styles.head}>
            <Text style={styles.title}>{row.name}</Text>
            <Text style={styles.big}>{percent(row.average_percentage)}</Text>
          </View>
          <Text style={styles.email}>{row.email}</Text>
          <Text style={type.small}>
            {row.courses} courses · {row.attempts} attempts · {row.marks || 'no marks yet'}
          </Text>
        </Surface>
      )) : null}

      {data && tab === 'modules' ? (
        data.modules.length === 0 ? (
          <Empty title="No module data yet" body="Nobody has taken a module quiz." />
        ) : data.modules.map((row) => (
          <Surface key={row.id}>
            <View style={styles.head}>
              <Text style={styles.title} numberOfLines={1}>{row.title}</Text>
              <Text style={styles.big}>{percent(row.average_percentage)}</Text>
            </View>
            <Text style={type.small}>{row.course_code} · {row.chapter} · {row.attempts} attempts</Text>
          </Surface>
        ))
      ) : null}

      {data && tab === 'skills' ? (
        data.skills.length === 0 ? (
          <Empty title="No quiz answers yet" body="Skill accuracy appears once students sit quizzes." />
        ) : (
          <Surface>
            {data.skills.map((row) => (
              <View key={row.skill} style={styles.row}>
                <Text style={styles.rowLabel}>{row.skill}</Text>
                <Text style={styles.rowValue}>
                  {row.correct}/{row.asked} ({row.accuracy}%)
                </Text>
              </View>
            ))}
          </Surface>
        )
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
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  code: {
    fontFamily: mono,
    fontSize: 12,
    color: colors.accent,
    backgroundColor: colors.accentSoft,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    overflow: 'hidden',
  },
  chip: {
    fontSize: 11.5,
    fontWeight: '700',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    overflow: 'hidden',
  },
  chipQuiet: {
    fontSize: 11.5,
    color: colors.muted,
    backgroundColor: colors.canvas,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    overflow: 'hidden',
  },
  title: { fontSize: 16.5, fontWeight: '700', color: colors.ink, marginTop: 8, flexShrink: 1 },
  email: { fontSize: 13, color: colors.muted, marginBottom: 4 },
  big: { fontSize: 20, fontWeight: '700', color: colors.accent },
  note: { fontSize: 12.5, color: colors.accent, marginTop: 6 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
    marginTop: 8,
  },
  rowLabel: { fontSize: 14, color: colors.inkSoft, flex: 1, paddingRight: 10 },
  rowValue: { fontFamily: mono, fontSize: 13, color: colors.ink },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  search: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    borderRadius: radius.control,
    backgroundColor: colors.paper,
    paddingHorizontal: 13,
    paddingVertical: 12,
    fontSize: 15,
    color: colors.ink,
    marginBottom: spacing(1.5),
  },
  filterRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing(1.5) },
  filter: {
    borderWidth: 1,
    borderColor: colors.grid,
    backgroundColor: colors.paper,
    borderRadius: radius.control,
    paddingHorizontal: 12,
    paddingVertical: 9,
    marginRight: 8,
    marginBottom: 8,
  },
  filterActive: { backgroundColor: colors.tabActive, borderColor: colors.tabActive },
  filterText: { fontSize: 13.5, fontWeight: '600', color: colors.inkSoft },
  actionRow: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 12 },
  action: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    borderRadius: radius.control,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
    marginBottom: 8,
  },
  actionText: { fontSize: 13, color: colors.inkSoft, fontWeight: '600' },
  quality: {
    backgroundColor: colors.canvas,
    borderRadius: radius.control,
    padding: 10,
    marginTop: 10,
  },
  qualityText: { fontSize: 12.5, color: colors.inkSoft, lineHeight: 19 },
  moduleRow: {
    flexDirection: 'row',
    paddingVertical: 9,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
    marginTop: 8,
  },
  moduleNumber: { fontFamily: mono, fontSize: 12, color: colors.muted, width: 26, marginTop: 3 },
  moduleTitle: { fontSize: 14.5, color: colors.ink, fontWeight: '600' },
  commentBox: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    borderRadius: radius.control,
    minHeight: 70,
    padding: 12,
    marginTop: 12,
    fontSize: 14.5,
    color: colors.ink,
    textAlignVertical: 'top',
  },
  history: { borderTopWidth: 1, borderTopColor: colors.grid, marginTop: 12, paddingTop: 10 },
  historyLine: { fontSize: 12.5, color: colors.muted, marginTop: 4 },
});
