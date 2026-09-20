import type {GIKind} from '../../../packages/domain/interventions';

export const INTERVENTION_COLOURS:Record<GIKind,[number,number,number,number]>={
 rain_garden:[122,214,112,170],
 bioswale:[90,220,181,175],
 permeable_pavement:[216,197,129,175],
 detention_basin:[103,188,231,175],
};

export const INTERVENTION_NAMES:Record<GIKind,string>={
 rain_garden:'Rain garden',bioswale:'Bioswale',permeable_pavement:'Permeable pavement',detention_basin:'Detention basin',
};

export const INTERVENTION_STORIES:Record<GIKind,string>={
 rain_garden:'Shallow planted storage slows runoff and lets water infiltrate.',
 bioswale:'A graded planted channel conveys, slows and infiltrates runoff.',
 permeable_pavement:'A durable surface opens storage below the street.',
 detention_basin:'A surface depression holds the peak and releases it deliberately.',
};
