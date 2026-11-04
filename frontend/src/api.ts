export interface Ticket { ticket_id:string; subject:string; description:string; category?:string; resolution_notes?:string; tags?:string[]; created_at?:string; status?:string }
export interface Match { ticket:Ticket; applicability?:string; differences?:string[]; outcome:string; outcome_source:string; matched_terms?:string[]; cosine_similarity?:number; keyword_rank?:number; semantic_rank?:number }
export interface SearchResult { matches:Match[]; assessment:string; reference_date:string; history_months:number; searched_tickets?:number; method:string; synthetic_feedback_enabled?:boolean }
export async function request<T>(path:string, options:RequestInit = {}):Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 45000);
  try {
    const response = await fetch(`/api${path}`, {...options, signal:controller.signal, headers:{'Content-Type':'application/json',...options.headers}});
    if (!response.ok) {
      if (response.status === 404) throw new Error('This ticket was not found in the active history.');
      if (response.status === 422) throw new Error('Check the ticket text and result limit, then try again.');
      throw new Error('The support service is unavailable. Check that the backend is running and its database connection is available.');
    }
    return await response.json() as T;
  } catch(error) {
    if (error instanceof Error && error.name === 'AbortError') throw new Error('The request took too long. Please try again.');
    throw error instanceof TypeError ? new Error('Cannot reach the support service. Check your connection and retry.') : error;
  } finally { window.clearTimeout(timeout); }
}
