import React, { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function DockerStatsForm() {
  const [form, setForm] = useState({
    container: "first_test",
    image: "one/ad-base:v2",
    bashFile: "source DemoAD_start.sh",
    gpu: false,
    memory: "1g",
    memoryReservation: "999m",
    cpus: "1",
    cpusetCpus: "2",
    gpus: "device=0",
    interval: 0.5,
    iterations: 100,
  });

  const handleChange = (key, value) => {
    setForm({ ...form, [key]: value });
  };

  return (
    <Card className="max-w-2xl mx-auto p-6 space-y-4">
      <CardContent className="space-y-4">
        <div>
          <Label>Container Name</Label>
          <Input value={form.container} onChange={(e) => handleChange("container", e.target.value)} />
        </div>
        <div>
          <Label>Image Name</Label>
          <Input value={form.image} onChange={(e) => handleChange("image", e.target.value)} />
        </div>
        <div>
          <Label>Bash File Command</Label>
          <Input value={form.bashFile} onChange={(e) => handleChange("bashFile", e.target.value)} />
        </div>
        <div>
          <Label>GPU Enabled</Label>
          <Input type="checkbox" checked={form.gpu} onChange={(e) => handleChange("gpu", e.target.checked)} />
        </div>
        <div>
          <Label>Memory</Label>
          <Input value={form.memory} onChange={(e) => handleChange("memory", e.target.value)} />
        </div>
        <div>
          <Label>Memory Reservation</Label>
          <Input value={form.memoryReservation} onChange={(e) => handleChange("memoryReservation", e.target.value)} />
        </div>
        <div>
          <Label>CPUs</Label>
          <Input value={form.cpus} onChange={(e) => handleChange("cpus", e.target.value)} />
        </div>
        <div>
          <Label>CPU Set (e.g. 2 or 0,1)</Label>
          <Input value={form.cpusetCpus} onChange={(e) => handleChange("cpusetCpus", e.target.value)} />
        </div>
        <div>
          <Label>GPUs (e.g. device=0)</Label>
          <Input value={form.gpus} onChange={(e) => handleChange("gpus", e.target.value)} />
        </div>
        <div>
          <Label>Interval (seconds)</Label>
          <Input type="number" step="0.1" value={form.interval} onChange={(e) => handleChange("interval", parseFloat(e.target.value))} />
        </div>
        <div>
          <Label>Number of Iterations</Label>
          <Input type="number" value={form.iterations} onChange={(e) => handleChange("iterations", parseInt(e.target.value))} />
        </div>

        <Button className="mt-4">Submit</Button>
      </CardContent>
    </Card>
  );
}
