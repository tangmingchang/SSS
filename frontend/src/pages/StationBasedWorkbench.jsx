import React from 'react';
import WorkbenchLayout from '../components/workbench/WorkbenchLayout';
import './StationBasedWorkbench.css';

/**
 * 站点式装配线工作台主页面
 * 替换原有的WorkbenchPage，使用新的站点式布局
 */
export default function StationBasedWorkbench({
  publicResources = { characters: [], scenes: [], motions: [] },
  personalResources = { characters: [], scenes: [], motions: [] },
  onAddToPersonal,
}) {
  // 合并资源库数据
  const allCharacters = React.useMemo(() => [
    ...publicResources.characters.map((char) => ({
      id: char.id,
      name: char.name,
      thumbnail: char.thumbnail || null,
      images: char.images || null,
      image_url: char.images?.full || char.image_url || null,
      description: `${char.name} - ${char.style || '传统皮影角色'}`,
    })),
    ...personalResources.characters.map((char) => ({
      id: char.id,
      name: char.name,
      thumbnail: char.thumbnail || null,
      images: char.images || null,
      image_url: char.images?.full || char.image_url || null,
      description: `${char.name} - 个人资源`,
    })),
  ], [publicResources.characters, personalResources.characters]);

  const allScenes = React.useMemo(() => [
    ...publicResources.scenes,
    ...personalResources.scenes,
  ], [publicResources.scenes, personalResources.scenes]);

  return (
    <div className="station-based-workbench">
      <WorkbenchLayout
        allCharacters={allCharacters}
        allScenes={allScenes}
        onAddToPersonal={onAddToPersonal}
      />
    </div>
  );
}
