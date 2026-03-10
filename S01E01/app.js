require('dotenv').config({ path: '../.env' });

const personSchema = {
  name: "response",
  strict: true,
  schema: {
    type: "object",
    properties: {
      people: {
        type: "array",
        items: {
          type: "object",
          properties: {
            name: {
              type: ["string"],
              description: "First name of the person."
            },
            surname: {
              type: ["string"],
              description: "Surname of the person."
            },
            gender: {
              type: ["string"],
              enum: ["F", "M"],
              description: "Gender of the person, F for female, M for male."
            },
            born: {
              type: ["integer"],
              description: "Birth year of the person as an integer."
            },
            city: {
              type: ["string"],
              description: "Birth place of the person."
            },
            tags: {
              type: "array",
              items: {
                type: "string",
                enum: ["IT", "transport", "edukacja", "medycyna", "praca z ludźmi", "praca z pojazdami", "praca fizyczna"]
              },
              description: "List of tags describing the person's field or work type."
            }
          },
          required: ["name", "surname", "gender", "born", "city", "tags"],
          additionalProperties: false
        }
      }
    },
    required: ["people"],
    additionalProperties: false
  }
};

async function fetch_people() {
  console.log('Fetching people...');
  const response = await fetch(`https://hub.ag3nts.org/data/${process.env.AI_DEVS_API_KEY}/people.csv`);
  if (!response.ok) {
    throw new Error('Failed to fetch people');
  }
  const csvText = await response.text();
  const lines = csvText.trim().split('\n');
  const headers = lines[0].split(',');
  return lines.slice(1).map(line => {
    const values = line.split(',');
    const obj = {};
    headers.forEach((header, i) => {
      obj[header] = values[i];
    });
    obj.age = 2026 - new Date(obj.birthDate).getFullYear();
    return obj;
  });
}


async function callOpenRouter(people) {
  console.log("Calling OpenRouter API...");
  const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      model: 'openai/gpt-4o-mini',
      messages: [
        { role: 'system', content: 'Assign tags based on the description.' },
        { role: 'user', content: JSON.stringify(people) }
      ],
      response_format: {
        type: "json_schema",
        json_schema: personSchema
      }
    })
  });

  const data = await response.json();
  console.log("Full response:", data);
  console.log("Model message:", data.choices[0].message.content);
  return data.choices[0].message.content;
}

(async () => {
    const people = await fetch_people();
    console.log('Example person:', people[0]);
    console.log('Fetched people data:', people.length);

    const people1 = people.filter(person => person.gender === "M");
    console.log('Filtered people (gender = M):', people1.length);

    const people2 = people1.filter(person => person.birthPlace === "Grudziądz");
    console.log('Filtered people (birthPlace = Grudziądz):', people2.length);

    const people3 = people2.filter(person => {
      const age = 2026 - new Date(person.birthDate).getFullYear();
      return age >= 20 && age <= 40;
    });
    console.log('Filtered people (age 20-40):', people3.length);

    console.log(people3);

    const tagged = JSON.parse(await callOpenRouter(people3));

    const transport = tagged.people.filter(person => person.tags.includes("transport"));
    console.log('People tagged with transport:', transport);
})();
