import React, { useCallback, useEffect, useState } from 'react';
import { Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import api, { readError } from '../../api/client';
import { Button, Loading, Notice, Surface } from '../../components/ui';
import { useAuth } from '../../store/auth';
import { colors, mono, spacing, type } from '../../theme';

const HEADINGS = [
  'In plain words',
  'The main ideas',
  'Excel terms used here',
  'Try it yourself',
  'Check yourself',
];

// The explanation comes back as plain text with known headings, so it is rendered
// as real headings and paragraphs instead of one wall of text.
function Explanation({ text }) {
  const lines = (text || '').split('\n');
  return (
    <View>
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) return <View key={index} style={{ height: 10 }} />;
        if (HEADINGS.includes(trimmed)) {
          return (
            <Text key={index} style={styles.explanationHeading}>
              {trimmed}
            </Text>
          );
        }
        if (/^\d+\.\s/.test(trimmed) || trimmed.startsWith('- ')) {
          return (
            <View key={index} style={styles.listRow}>
              <Text style={styles.listMark}>{trimmed.startsWith('- ') ? '\u2022' : trimmed.split('.')[0]}</Text>
              <Text style={styles.listText}>{trimmed.replace(/^(\d+\.\s|-\s)/, '')}</Text>
            </View>
          );
        }
        return (
          <Text key={index} style={styles.paragraph}>
            {trimmed}
          </Text>
        );
      })}
    </View>
  );
}

<<<<<<< HEAD
// Pictures that came out of the uploaded book itself, shown under the explanation for
// the section they were printed in. A textbook explains as much with its screenshots as
// with its sentences, so they belong beside the reading rather than behind a link.
function Figures({ images }) {
  const list = Array.isArray(images) ? images.filter((item) => item.file_url) : [];
  if (!list.length) return null;
  return (
    <View style={styles.figures}>
      <Text style={styles.explanationHeading}>Pictures from the book</Text>
      {list.map((image) => (
        <View key={image.id} style={styles.figure}>
          <Image
            source={{ uri: image.file_url }}
            style={[
              styles.figureImage,
              image.width && image.height
                ? { aspectRatio: image.width / image.height, height: undefined }
                : null,
            ]}
            resizeMode="contain"
          />
          <Text style={styles.figureLabel}>{image.label}</Text>
          {image.caption ? <Text style={styles.figureCaption}>{image.caption}</Text> : null}
        </View>
      ))}
    </View>
  );
}

=======
>>>>>>> origin/main
export default function ContentScreen({ route, navigation }) {
  const { kind, id, title } = route.params;
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [resources, setResources] = useState([]);
  const [demos, setDemos] = useState([]);
  const [error, setError] = useState('');
  const [showSource, setShowSource] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    async (refresh = false) => {
      setError('');
      if (refresh) setBusy(true);
      try {
        const path = kind === 'chapter' ? `/chapters/${id}/` : `/modules/${id}/`;
        const { data: payload } = await api.get(`${path}${refresh ? '?refresh=1' : ''}`);
        setData(payload);
        // References and walkthroughs are extras. If the server has not got them, the
        // reading still opens; it just has nothing hanging off it.
        const key = kind === 'chapter' ? 'chapter' : 'module';
        const [res, demo] = await Promise.all([
          api.get(`/resources/?${key}=${id}`).catch(() => ({ data: [] })),
          api.get(`/demonstrations/?${key}=${id}`).catch(() => ({ data: [] })),
        ]);
        setResources(Array.isArray(res.data) ? res.data : []);
        setDemos(Array.isArray(demo.data) ? demo.data : []);
      } catch (err) {
        setError(readError(err));
      } finally {
        setBusy(false);
      }
    },
    [kind, id]
  );

  useEffect(() => {
    navigation.setOptions({ title: title || 'Reading' });
    load();
  }, [load, navigation, title]);

  if (!data && !error) return <Loading label="Writing the easy explanation" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Notice text={error} tone="error" />
      {data ? (
        <>
          <View style={styles.header}>
            <Text style={styles.kicker}>
              {kind === 'chapter'
                ? `Chapter ${data.number}`
                : `Module ${data.chapter_number}.${data.number}`}
            </Text>
            <Text style={type.title}>{data.title}</Text>
          </View>

          <Surface>
            <Explanation text={data.explanation} />
<<<<<<< HEAD
            <Figures images={data.images} />
=======
>>>>>>> origin/main
          </Surface>

          {resources.length ? (
            <Surface>
              <Text style={styles.sectionHeading}>Your instructor's references</Text>
              {resources.map((resource) => (
                <View key={resource.id} style={styles.resource}>
                  <Text style={styles.resourceTitle}>{resource.title}</Text>
                  {resource.caption ? (
                    <Text style={styles.resourceCaption}>{resource.caption}</Text>
                  ) : null}
                  {resource.kind === 'IMAGE' && resource.file_url ? (
                    <Image
                      source={{ uri: resource.file_url }}
                      style={styles.resourceImage}
                      resizeMode="contain"
                    />
                  ) : resource.url ? (
                    <Text style={styles.resourceLink}>{resource.url}</Text>
                  ) : resource.file_url ? (
                    <Text style={styles.resourceLink}>{resource.file_url}</Text>
                  ) : null}
                </View>
              ))}
            </Surface>
          ) : null}

          {demos.map((demo) => (
            <Surface key={demo.id}>
              <Text style={styles.sectionHeading}>{demo.title}</Text>
              {demo.summary ? <Text style={styles.paragraph}>{demo.summary}</Text> : null}
              {(demo.steps || []).map((step) => (
                <View key={step.order} style={styles.step}>
                  <Text style={styles.stepNumber}>{step.order}</Text>
                  <View style={{ flex: 1 }}>
                    {step.title ? <Text style={styles.stepTitle}>{step.title}</Text> : null}
                    <Text style={styles.stepText}>{step.instruction}</Text>
                    {step.cell || step.formula ? (
                      <Text style={styles.stepCell}>
                        {[step.cell, step.formula].filter(Boolean).join('  ')}
                      </Text>
                    ) : null}
                  </View>
                </View>
              ))}
              <Text style={styles.demoNote}>
                A walkthrough from {demo.created_by_name || 'your instructor'}.
              </Text>
            </Surface>
          ))}

          <Pressable onPress={() => setShowSource((prev) => !prev)} style={styles.toggle}>
            <Text style={styles.toggleText}>
              {showSource ? 'Hide the text from the book' : 'Show the text from the book'}
            </Text>
          </Pressable>

          {showSource ? (
            <Surface>
              <Text style={styles.sourceLabel}>Extracted from the uploaded file</Text>
              <Text style={styles.sourceText}>{data.raw_text}</Text>
            </Surface>
          ) : null}

          {user?.role === 'STUDENT' ? (
            <Button
              tone="accent"
              label="Take the quiz on this section"
              onPress={() =>
                navigation.navigate('Quiz', {
                  kind,
                  id,
                  title: data.title,
                })
              }
              style={{ marginBottom: spacing(1) }}
            />
          ) : (
            <Button
              tone="accent"
              label="Question sets for this section"
              onPress={() => navigation.navigate('QuizPreview', { kind, id, title: data.title })}
              style={{ marginBottom: spacing(1) }}
            />
          )}
          <Button
            tone="quiet"
            label={busy ? 'Rewriting' : 'Rewrite the explanation'}
            disabled={busy}
            onPress={() => load(true)}
          />
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
  header: { marginBottom: spacing(2) },
  kicker: { fontFamily: mono, fontSize: 12, color: colors.accent, marginBottom: 4 },
  explanationHeading: {
    fontSize: 16,
    fontWeight: '700',
    color: colors.ink,
    marginTop: spacing(1.5),
    marginBottom: 6,
  },
  paragraph: { fontSize: 15, lineHeight: 24, color: colors.ink, marginBottom: 6 },
  listRow: { flexDirection: 'row', marginBottom: 6, paddingRight: 6 },
  listMark: { fontFamily: mono, fontSize: 13, color: colors.accent, width: 22, marginTop: 3 },
  listText: { flex: 1, fontSize: 15, lineHeight: 23, color: colors.ink },
  toggle: { paddingVertical: spacing(1.5) },
  toggleText: { color: colors.accent, fontWeight: '600', fontSize: 14 },
  sectionHeading: { fontSize: 16.5, fontWeight: '700', color: colors.ink, marginBottom: 8 },
<<<<<<< HEAD
  figures: { marginTop: spacing(2) },
  figure: { marginBottom: spacing(2) },
  figureImage: {
    width: '100%',
    height: 260,
    borderWidth: 1,
    borderColor: colors.grid,
    borderRadius: 8,
    backgroundColor: colors.canvas,
  },
  figureLabel: { fontFamily: mono, fontSize: 11.5, color: colors.accent, marginTop: 6 },
  figureCaption: { fontSize: 13.5, color: colors.inkSoft, lineHeight: 20, marginTop: 3 },
=======
>>>>>>> origin/main
  resource: { marginBottom: 14 },
  resourceTitle: { fontSize: 14.5, fontWeight: '600', color: colors.ink },
  resourceCaption: { fontSize: 13, color: colors.muted, marginTop: 2, lineHeight: 19 },
  resourceImage: {
    width: '100%',
    height: 240,
    marginTop: 8,
    borderWidth: 1,
    borderColor: colors.grid,
    borderRadius: 8,
    backgroundColor: colors.canvas,
  },
  resourceLink: { fontFamily: mono, fontSize: 12, color: colors.accent, marginTop: 6 },
  step: { flexDirection: 'row', marginBottom: 10 },
  stepNumber: {
    fontFamily: mono,
    fontSize: 12,
    color: colors.paper,
    backgroundColor: colors.accent,
    width: 22,
    height: 22,
    borderRadius: 11,
    textAlign: 'center',
    lineHeight: 22,
    marginRight: 10,
    overflow: 'hidden',
  },
  stepTitle: { fontSize: 14.5, fontWeight: '600', color: colors.ink },
  stepText: { fontSize: 14.5, color: colors.inkSoft, lineHeight: 21 },
  stepCell: { fontFamily: mono, fontSize: 12.5, color: colors.accent, marginTop: 3 },
  demoNote: { fontSize: 12, color: colors.muted, marginTop: 4 },
  sourceLabel: { fontSize: 12, color: colors.muted, marginBottom: 8 },
  sourceText: { fontFamily: mono, fontSize: 12, lineHeight: 20, color: colors.inkSoft },
});
