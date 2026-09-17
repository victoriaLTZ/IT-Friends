const DEFAULT_AVATAR = {
  skin: '#F5C4B3',
  hairStyle: 'court',
  hairColor: '#4A1B0C',
  eyes: 'normal',
  outfitColor: '#D85A30',
  accessory: 'none',
};

const HAIR_PATHS = {
  court: "M58 90 Q60 30 110 30 Q160 30 162 90 Q140 55 110 55 Q80 55 58 90 Z",
  long: "M55 90 Q58 25 110 25 Q162 25 165 90 L165 150 Q150 150 150 100 Q150 55 110 55 Q70 55 70 100 Q70 150 55 150 Z",
  boule: "M58 95 Q55 20 110 20 Q165 20 162 95 Q165 60 110 60 Q55 60 58 95 Z",
};

function buildEyes(type) {
  if (type === 'coeur') {
    return `<path d="M86 98 Q86 92 92 92 Q98 92 98 98 Q98 104 92 108 Q86 104 86 98 Z" fill="#D4537E"/>
            <path d="M122 98 Q122 92 128 92 Q134 92 134 98 Q134 104 128 108 Q122 104 122 98 Z" fill="#D4537E"/>`;
  }
  if (type === 'fermes') {
    return `<path d="M84 100 Q92 106 100 100" stroke="#2B2620" stroke-width="3" fill="none" stroke-linecap="round"/>
            <path d="M120 100 Q128 106 136 100" stroke="#2B2620" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  }
  if (type === 'etonne') {
    return `<circle cx="92" cy="100" r="9" fill="#2B2620"/><circle cx="128" cy="100" r="9" fill="#2B2620"/>`;
  }
  return `<circle cx="92" cy="100" r="6" fill="#2B2620"/><circle cx="128" cy="100" r="6" fill="#2B2620"/>`;
}

function buildAccessory(type) {
  if (type === 'lunettes') {
    return `<circle cx="92" cy="100" r="14" fill="none" stroke="#2B2620" stroke-width="3"/>
            <circle cx="128" cy="100" r="14" fill="none" stroke="#2B2620" stroke-width="3"/>
            <line x1="106" y1="100" x2="114" y2="100" stroke="#2B2620" stroke-width="3"/>`;
  }
  if (type === 'chapeau') {
    return `<ellipse cx="110" cy="48" rx="50" ry="8" fill="#2B2620"/>
            <path d="M80 48 Q80 15 110 15 Q140 15 140 48 Z" fill="#2B2620"/>`;
  }
  return '';
}

function buildAvatarInner(cfg) {
  const c = cfg || DEFAULT_AVATAR;
  return `
    <ellipse cx="110" cy="205" rx="46" ry="8" fill="#EDE3D0"/>
    <rect x="70" y="130" width="80" height="70" rx="18" fill="${c.outfitColor}"/>
    <circle cx="110" cy="95" r="52" fill="${c.skin}"/>
    <path d="${HAIR_PATHS[c.hairStyle]}" fill="${c.hairColor}"/>
    ${buildEyes(c.eyes)}
    <path d="M95 118 Q110 128 125 118" stroke="#2B2620" stroke-width="3" fill="none" stroke-linecap="round"/>
    ${buildAccessory(c.accessory)}
  `;
}