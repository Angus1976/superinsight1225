/**
 * Temp data API — 薄封装，上传时间映射为列表用的 createdAt。
 */
import { dataLifecycleApi, type TempData as ApiTempData } from '@/services/dataLifecycle';

export type TempData = {
  id: string;
  name: string;
  state: string;
  createdAt: string;
  updatedAt?: string;
};

function mapTemp(t: ApiTempData): TempData {
  return {
    id: t.id,
    name: t.name,
    state: t.state,
    createdAt: t.uploaded_at,
    updatedAt: t.updated_at,
  };
}

export const tempDataApi = {
  async list(page: number, pageSize: number) {
    const res = await dataLifecycleApi.listTempData({
      page,
      page_size: pageSize,
    });
    return {
      items: res.items.map(mapTemp),
      total: res.total,
      page: res.page,
      page_size: res.page_size,
    };
  },
  delete: (id: string) => dataLifecycleApi.deleteTempData(id),
  archive: (id: string) => dataLifecycleApi.archiveTempData(id),
  restore: (id: string) => dataLifecycleApi.restoreTempData(id),
};
