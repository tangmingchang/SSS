import React from 'react';
import { resolveImageUrl } from '../../utils/api';
import './StageBackground.css';

/**
 * 舞台背景层组件
 */
export default function StageBackground({ background }) {
  if (!background) {
    return (
      <div className="stage-background default">
        <div className="stage-curtain"></div>
      </div>
    );
  }

  return (
    <div className="stage-background">
      <img
        src={resolveImageUrl(background.url || background.thumbnail || background.image_url)}
        alt={background.name || '背景'}
        className="background-image"
      />
      <div className="stage-curtain"></div>
    </div>
  );
}
