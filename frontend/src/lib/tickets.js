import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "./api";

export function useTickets(params) {
  return useQuery({
    queryKey: ["tickets", params],
    queryFn: async () => {
      const { data } = await api.get("/tickets", { params });
      return data;
    },
    keepPreviousData: true,
  });
}

export function useTicket(id) {
  return useQuery({
    queryKey: ["ticket", id],
    queryFn: async () => (await api.get(`/tickets/${id}`)).data,
  });
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload) => (await api.post("/tickets", payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tickets"] }),
  });
}

export function useUpdateTicket(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (changes) => (await api.patch(`/tickets/${id}`, changes)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ticket", id] });
      qc.invalidateQueries({ queryKey: ["tickets"] });
      qc.invalidateQueries({ queryKey: ["activity", id] });
    },
  });
}

export function useComments(id) {
  return useQuery({
    queryKey: ["comments", id],
    queryFn: async () => (await api.get(`/tickets/${id}/comments`)).data,
  });
}

export function useAddComment(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body) => (await api.post(`/tickets/${id}/comments`, { body })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["comments", id] });
      qc.invalidateQueries({ queryKey: ["activity", id] });
    },
  });
}

export function useActivity(id) {
  return useQuery({
    queryKey: ["activity", id],
    queryFn: async () => (await api.get(`/tickets/${id}/activity`)).data,
  });
}

export function useAgents(enabled) {
  return useQuery({
    queryKey: ["agents"],
    queryFn: async () => (await api.get("/users/agents")).data,
    enabled,
  });
}
