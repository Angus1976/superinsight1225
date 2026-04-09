/**
 * Review API — 薄封装，camelCase 字段供旧列表使用。
 */
import { dataLifecycleApi, type Review as ApiReview } from '@/services/dataLifecycle';

export type Review = {
  id: string;
  targetType: string;
  targetId: string;
  requester: string;
  status: ApiReview['status'];
  submittedAt: string;
  reviewer?: string;
};

function mapReview(r: ApiReview): Review {
  return {
    id: r.id,
    targetType: r.target_type,
    targetId: r.target_id,
    requester: r.requester,
    status: r.status,
    submittedAt: r.submitted_at,
    reviewer: r.reviewer,
  };
}

export const reviewApi = {
  async list(page: number, pageSize: number) {
    const res = await dataLifecycleApi.listReviews({
      page,
      page_size: pageSize,
    });
    return {
      items: res.items.map(mapReview),
      total: res.total,
      page: res.page,
      page_size: res.page_size,
    };
  },
  approve: (id: string) => dataLifecycleApi.approveReview(id),
  reject: (id: string, reason: string) => dataLifecycleApi.rejectReview(id, reason),
  cancel: (id: string) => dataLifecycleApi.cancelReview(id),
};
