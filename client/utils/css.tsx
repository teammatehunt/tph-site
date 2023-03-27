import CSS from 'csstype';

function hyphenateCamelCase(input: string): string {
  return input.replace(/([a-z][A-Z])/g, (g) => g[0] + '-' + g[1].toLowerCase());
}

export function cssToString(css: CSS.Properties): string {
  return Object.entries(css)
    .map(([key, value]) => `${hyphenateCamelCase(key)}: ${value};`)
    .join(' ');
}
