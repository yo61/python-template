export default {
  extends: ['@commitlint/config-conventional'],
  // Dependabot generates bodies with long markdown URLs that exceed
  // body-max-line-length and will not wrap them. Skip its commits; the full
  // ruleset still applies to human authors.
  ignores: [(message) => message.includes('Signed-off-by: dependabot[bot]')],
  rules: {
    // `deps` is not a config-conventional type. Dependabot uses it so
    // release-please can route those commits to a visible Dependencies
    // changelog section -- the default `chore(deps)` lands under `chore`,
    // which the preset hides.
    'type-enum': [
      2,
      'always',
      [
        'build',
        'chore',
        'ci',
        'deps',
        'docs',
        'feat',
        'fix',
        'perf',
        'refactor',
        'revert',
        'style',
        'test',
      ],
    ],
    // Allow class names and acronyms in subjects. The default ruleset rejects
    // pascal-case/start-case subjects, too restrictive for domain-rich code.
    'subject-case': [0],
  },
};
