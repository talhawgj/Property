"use client";
import React, { useState, useEffect } from "react";

interface LeadItem {
  client_brokerage: string;
  contact_person: string;
  contact_phone: string;
  contact_email: string;
  county: string;
  master_phone: string;
}

const BACKEND_API_URL =
  process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://10.8.0.1:8001";

const LeadPage = () => {
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLeads = async (): Promise<LeadItem[]> => {
      // Returns array, not single item
      try {
        const response = await fetch(`${BACKEND_API_URL}/lead-clients`);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: LeadItem[] = await response.json();
        return data;
      } catch (err) {
        console.error("Error fetching leads:", err);
        throw err;
      }
    };

    const loadLeads = async () => {
      try {
        setLoading(true);
        const data = await fetchLeads();
        setLeads(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch leads");
      } finally {
        setLoading(false);
      }
    };

    loadLeads();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="w-full h-auto p-4 bg-white container mx-auto flex gap-4">
      <div className="flex-1 h-auto max-h-full">
        {leads ? leads.map((key, idx) => <div></div>) : ""}
      </div>
      <div className="flex-1 h-auto max-h-full">
        <div className="max-h-[50%] flex-1 h-auto"></div>
        <div className="max-h-[50%] flex-1 h-auto"></div>
      </div>
    </div>
  );
};

export default LeadPage;
